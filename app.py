import streamlit as st
from streamlit_option_menu import option_menu
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
import hashlib
import re
import random
import string
from PIL import Image
import qrcode
import io
import base64
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import plotly.express as px
import plotly.graph_objects as go

# ---------- Helper Functions ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def validate_pan(pan):
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    return bool(re.match(pattern, pan))

def validate_name(name):
    """Allow only alphabets and spaces"""
    return bool(re.match(r'^[A-Za-z\s]+$', name))

def generate_account_number():
    return ''.join(random.choices(string.digits, k=12))

def format_currency(amount):
    return f"₹{amount:,.2f}"

def generate_qr_code(data):
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(str(data))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        return img
    except Exception:
        return None

def decode_qr_code(image_file):
    try:
        from pyzbar.pyzbar import decode
        img = Image.open(image_file)
        decoded_objects = decode(img)
        if decoded_objects:
            return decoded_objects[0].data.decode('utf-8')
        return None
    except Exception:
        return None

def calculate_fd_maturity(principal, tenure_months, rate=7.5):
    rate_yearly = rate / 100
    quarters = tenure_months / 3
    maturity = principal * (1 + rate_yearly/4) ** quarters
    return round(maturity, 2)

def calculate_sip_future(sip_amount, months, expected_return=12):
    monthly_rate = expected_return / 100 / 12
    future_value = sip_amount * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    return round(future_value, 2)

# ---------- Database Manager ----------
class DatabaseManager:
    def __init__(self, db_path="banking.db"):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def initialize_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                pan TEXT UNIQUE NOT NULL,
                photo_path TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_type TEXT NOT NULL,
                account_number TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0.0,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_account_id INTEGER,
                to_account_id INTEGER,
                amount REAL NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                fraud_score REAL DEFAULT 0.0,
                FOREIGN KEY (from_account_id) REFERENCES accounts(id),
                FOREIGN KEY (to_account_id) REFERENCES accounts(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fraud_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                alert_message TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                reviewed INTEGER DEFAULT 0,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                join_date DATE,
                salary REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_from ON transactions(from_account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_to ON transactions(to_account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)")
        
        # Create default admin if not exists
        cursor.execute("SELECT id FROM users WHERE is_admin = 1")
        if not cursor.fetchone():
            admin_pw = hash_password("Admin@123")
            cursor.execute("INSERT INTO users (email, password_hash, full_name, pan, photo_path, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                           ("admin@banking.com", admin_pw, "System Admin", "ADMIN9999A", "", 1))
            admin_id = cursor.lastrowid
            cursor.execute("INSERT INTO accounts (user_id, account_type, account_number, balance) VALUES (?, ?, ?, ?)",
                           (admin_id, "Savings", "ADMIN001", 1000000))
        
        # Insert sample employees if empty
        cursor.execute("SELECT COUNT(*) FROM employees")
        if cursor.fetchone()[0] == 0:
            sample_employees = [
                ("Rajesh Kumar", "Branch Manager", "rajesh@banking.com", "9876543210", "2023-01-15", 75000),
                ("Priya Sharma", "Loan Officer", "priya@banking.com", "9876543211", "2023-02-20", 55000),
                ("Amit Verma", "Customer Support", "amit@banking.com", "9876543212", "2023-03-10", 35000),
            ]
            cursor.executemany("INSERT INTO employees (name, role, email, phone, join_date, salary) VALUES (?,?,?,?,?,?)", sample_employees)
        
        conn.commit()
        conn.close()

# ---------- Fraud Detector ----------
class FraudDetector:
    def __init__(self, db_manager, model_path="fraud_model.pkl"):
        self.db = db_manager
        self.model_path = model_path
        self.model = None
    
    def extract_features(self, df_transactions):
        if len(df_transactions) == 0:
            return pd.DataFrame()
        features = pd.DataFrame()
        features['amount'] = df_transactions['amount']
        features['hour'] = pd.to_datetime(df_transactions['timestamp']).dt.hour
        features['day_of_week'] = pd.to_datetime(df_transactions['timestamp']).dt.dayofweek
        features['amount_log'] = np.log1p(df_transactions['amount'])
        features['amount_mean_rolling'] = df_transactions['amount'].rolling(window=5, min_periods=1).mean()
        features['amount_std_rolling'] = df_transactions['amount'].rolling(window=5, min_periods=1).std().fillna(0)
        return features.fillna(0)
    
    def train_model(self, force_retrain=False):
        if not force_retrain and os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            return
        conn = self.db.get_connection()
        transactions = pd.read_sql_query("SELECT id, amount, timestamp FROM transactions WHERE status = 'completed' ORDER BY timestamp", conn)
        conn.close()
        if len(transactions) < 10:
            np.random.seed(42)
            normal_amounts = np.random.exponential(5000, 200)
            fraud_amounts = np.random.uniform(20000, 100000, 20)
            amounts = np.concatenate([normal_amounts, fraud_amounts])
            timestamps = [datetime.now()] * len(amounts)
            synthetic_df = pd.DataFrame({'amount': amounts, 'timestamp': timestamps})
            features = self.extract_features(synthetic_df)
        else:
            features = self.extract_features(transactions)
        if len(features) > 0:
            self.model = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
            self.model.fit(features)
            joblib.dump(self.model, self.model_path)
    
    def predict_transaction_fraud(self, user_id, from_account_id, to_account_id, amount):
        if self.model is None:
            self.train_model()
        conn = self.db.get_connection()
        recent_txns = pd.read_sql_query("SELECT t.amount, t.timestamp FROM transactions t WHERE t.from_account_id = ? OR t.to_account_id = ? ORDER BY t.timestamp DESC LIMIT 20",
                                        conn, params=(from_account_id, from_account_id))
        conn.close()
        current_time = datetime.now()
        current_df = pd.DataFrame({'amount': [amount], 'timestamp': [current_time]})
        if len(recent_txns) > 0:
            combined = pd.concat([recent_txns, current_df], ignore_index=True)
            features = self.extract_features(combined)
            current_features = features.iloc[[-1]]
        else:
            current_features = self.extract_features(current_df)
        prediction = self.model.predict(current_features)[0]
        fraud_score = self.model.score_samples(current_features)[0]
        fraud_prob = 1 / (1 + np.exp(-fraud_score))
        is_fraud = (prediction == -1) or (fraud_prob > 0.7)
        return is_fraud, float(fraud_prob)
    
    def train_or_load_model(self):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
        else:
            self.train_model()

# ---------- Streamlit UI ----------
db = DatabaseManager()
db.initialize_database()
fraud_detector = FraudDetector(db)
fraud_detector.train_or_load_model()

st.set_page_config(page_title="AI Banking Suite", page_icon="🏦", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'selected' not in st.session_state:
    st.session_state.selected = "Dashboard"

def logout():
    for key in ['logged_in', 'user_id', 'user_email', 'is_admin']:
        st.session_state[key] = None if key != 'logged_in' else False
    st.session_state.logged_in = False
    st.session_state.selected = "Dashboard"
    st.rerun()

def get_user_accounts(user_id=None):
    if user_id is None:
        user_id = st.session_state.user_id
    conn = db.get_connection()
    accounts = pd.read_sql_query("SELECT * FROM accounts WHERE user_id = ?", conn, params=(user_id,))
    conn.close()
    return accounts

st.markdown("""
<style>
    .stButton > button { width: 100%; border-radius: 8px; background-color: #1E88E5; color: white; font-weight: bold; }
    .stButton > button:hover { background-color: #0D47A1; }
    .card { background-color: #262730; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #3A3B3C; }
    .metric-card { background-color: #1E1E2E; padding: 15px; border-radius: 8px; text-align: center; }
    .alert-danger { background-color: #ff4b4b20; border-left: 5px solid #ff4b4b; padding: 10px; border-radius: 5px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
if st.session_state.logged_in:
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/bank--v1.png", width=80)
        st.markdown(f"## Welcome, {st.session_state.user_email.split('@')[0]}")
        st.markdown("---")
        
        # Regular user menu
        if not st.session_state.is_admin:
            selected = option_menu(
                menu_title="Navigation",
                options=["Dashboard", "Accounts", "Money Transfer", "Transaction History", "Account Statements", "Profile"],
                icons=["house", "bank", "send", "clock-history", "file-text", "person-circle"],
                menu_icon="cast", default_index=0, orientation="vertical",
            )
        else:
            # Admin menu with submenu handling
            admin_main = option_menu(
                menu_title="Admin Navigation",
                options=["Dashboard", "Accounts", "Money Transfer", "Transaction History", "Account Statements", "Profile", "Admin Panel"],
                icons=["house", "bank", "send", "clock-history", "file-text", "person-circle", "shield"],
                menu_icon="cast", default_index=0, orientation="vertical",
            )
            if admin_main == "Admin Panel":
                admin_sub = option_menu(
                    menu_title="Admin Tools",
                    options=["Admin Dashboard", "Employee Management", "Bank Statements", "User Account Lookup"],
                    icons=["graph-up", "people", "file-earmark-text", "search"],
                    menu_icon="gear", default_index=0, orientation="vertical",
                )
                selected = admin_sub
            else:
                selected = admin_main
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
        st.markdown("---")
        st.caption("AI Banking Suite v1.0")

# Authentication
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏦 AI Banking Suite")
        st.markdown("### Welcome to Next-Gen Banking")
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, email, password_hash, is_admin FROM users WHERE email = ?", (email,))
                    user = cursor.fetchone()
                    conn.close()
                    if user and verify_password(password, user[2]):
                        st.session_state.logged_in = True
                        st.session_state.user_id = user[0]
                        st.session_state.user_email = user[1]
                        st.session_state.is_admin = bool(user[3])
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
        with tab2:
            with st.form("register_form"):
                full_name = st.text_input("Full Name", help="Only alphabets and spaces allowed")
                email = st.text_input("Email")
                pan = st.text_input("PAN Number")
                password = st.text_input("Password", type="password")
                confirm = st.text_input("Confirm Password", type="password")
                camera_photo = st.camera_input("Take a live photo")
                if st.form_submit_button("Register"):
                    if all([full_name, email, pan, password, confirm, camera_photo]):
                        if not validate_name(full_name):
                            st.error("Full name can only contain letters and spaces")
                        elif password != confirm:
                            st.error("Passwords do not match")
                        elif not validate_pan(pan):
                            st.error("Invalid PAN format (e.g., ABCDE1234F)")
                        else:
                            conn = db.get_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                            if cursor.fetchone():
                                st.error("Email already registered")
                            else:
                                cursor.execute("SELECT id FROM users WHERE pan = ?", (pan,))
                                if cursor.fetchone():
                                    st.error("PAN already registered")
                                else:
                                    os.makedirs("uploads", exist_ok=True)
                                    photo_path = f"uploads/user_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                                    with open(photo_path, "wb") as f:
                                        f.write(camera_photo.getvalue())
                                    hashed_pw = hash_password(password)
                                    cursor.execute("INSERT INTO users (email, password_hash, full_name, pan, photo_path, is_admin) VALUES (?,?,?,?,?,?)",
                                                   (email, hashed_pw, full_name, pan, photo_path, 0))
                                    user_id = cursor.lastrowid
                                    acc_num = generate_account_number()
                                    cursor.execute("INSERT INTO accounts (user_id, account_type, account_number, balance) VALUES (?,?,?,?)",
                                                   (user_id, 'Savings', acc_num, 5000.00))
                                    conn.commit()
                                    st.success("Registration successful! Please login.")
                                    st.rerun()
                            conn.close()
                    else:
                        st.warning("Please fill all fields and capture photo")

# Main application after login
if st.session_state.logged_in:
    # ---------- DASHBOARD (User & Admin) ----------
    if selected == "Dashboard":
        st.title("🏠 Dashboard")
        accounts = get_user_accounts()
        total_balance = accounts[accounts['account_type'].isin(['Savings', 'Current'])]['balance'].sum()
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Total Balance", f"₹{total_balance:,.2f}")
        with col2: st.metric("Active Accounts", len(accounts))
        with col3:
            conn = db.get_connection()
            txns = pd.read_sql_query("SELECT COUNT(*) as count FROM transactions WHERE from_account_id IN (SELECT id FROM accounts WHERE user_id=?) OR to_account_id IN (SELECT id FROM accounts WHERE user_id=?)",
                                     conn, params=(st.session_state.user_id, st.session_state.user_id))
            conn.close()
            st.metric("Total Transactions", txns.iloc[0]['count'])
        with col4:
            conn = db.get_connection()
            fraud_alerts = pd.read_sql_query("SELECT COUNT(*) as count FROM fraud_alerts fa JOIN transactions t ON fa.transaction_id = t.id WHERE t.from_account_id IN (SELECT id FROM accounts WHERE user_id=?)",
                                             conn, params=(st.session_state.user_id,))
            conn.close()
            st.metric("Fraud Alerts", fraud_alerts.iloc[0]['count'])
        
        st.subheader("📊 Your Accounts")
        for _, account in accounts.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([2,2,2,1])
                with c1:
                    st.markdown(f"**{account['account_type']}**\n{account['account_number']}")
                    if account['account_type'] in ['Fixed Deposit (FD)', 'Systematic Investment Plan (SIP)']:
                        meta = eval(account['metadata']) if account['metadata'] else {}
                        if account['account_type'] == 'Fixed Deposit (FD)':
                            tenure = meta.get('tenure_months', 12)
                            rate = meta.get('interest_rate', 7.5)
                            maturity = calculate_fd_maturity(account['balance'], tenure, rate)
                            st.caption(f"📈 {tenure} months @ {rate}% → Maturity: ₹{maturity:,.2f}")
                        else:
                            sip_amt = meta.get('sip_amount', account['balance'])
                            months = meta.get('months', 12)
                            future = calculate_sip_future(sip_amt, months)
                            st.caption(f"💰 Monthly SIP: ₹{sip_amt} → Future (12M): ₹{future:,.2f}")
                with c2: st.markdown(f"Balance: **₹{account['balance']:,.2f}**")
                with c3: st.caption("✅ Active" if account['account_type'] in ['Savings','Current'] else "🔒 Investment")
                with c4:
                    qr_img = generate_qr_code(account['account_number'])
                    if qr_img:
                        buf = io.BytesIO()
                        qr_img.save(buf, format="PNG")
                        buf.seek(0)
                        st.download_button("📱 QR", data=buf, file_name=f"qr_{account['account_number']}.png", mime="image/png", key=f"qr_{account['id']}")
                st.markdown("---")
    
    # ---------- ACCOUNTS (User) ----------
    elif selected == "Accounts":
        st.title("💳 Account Management")
        with st.expander("➕ Open New Account", expanded=False):
            acc_type = st.selectbox("Account Type", ["Savings", "Current", "Fixed Deposit (FD)", "Systematic Investment Plan (SIP)"])
            init_deposit = st.number_input("Initial Deposit (₹)", min_value=500.0, value=1000.0)
            
            fd_tenure = None
            fd_rate = None
            sip_monthly = None
            sip_months = None
            
            if acc_type == "Fixed Deposit (FD)":
                fd_tenure = st.selectbox("Tenure (months)", [6,12,24,36], index=1)
                fd_rate = 7.5 if fd_tenure <=12 else 8.0
                maturity_amt = calculate_fd_maturity(init_deposit, fd_tenure, fd_rate)
                st.info(f"Interest Rate: {fd_rate}% p.a. | Maturity Amount: ₹{maturity_amt:,.2f}")
            elif acc_type == "Systematic Investment Plan (SIP)":
                sip_monthly = st.number_input("Monthly Investment (₹)", min_value=500.0, value=1000.0)
                sip_months = st.selectbox("Tenure (months)", [12,24,36,60], index=0)
                future_val = calculate_sip_future(sip_monthly, sip_months, expected_return=12)
                st.info(f"Expected returns @12% p.a. → Future Value after {sip_months} months: ₹{future_val:,.2f}")
            
            if st.button("Open Account"):
                conn = db.get_connection()
                cursor = conn.cursor()
                if acc_type in ['Savings','Current']:
                    cursor.execute("SELECT id FROM accounts WHERE user_id=? AND account_type=?", (st.session_state.user_id, acc_type))
                    if cursor.fetchone():
                        st.error(f"You already have a {acc_type} account")
                    else:
                        acc_num = generate_account_number()
                        cursor.execute("INSERT INTO accounts (user_id, account_type, account_number, balance) VALUES (?,?,?,?)",
                                       (st.session_state.user_id, acc_type, acc_num, init_deposit))
                        conn.commit()
                        st.success(f"{acc_type} account opened! Number: {acc_num}")
                else:
                    acc_num = generate_account_number()
                    metadata = {}
                    if acc_type == "Fixed Deposit (FD)":
                        metadata = {"tenure_months": fd_tenure, "interest_rate": fd_rate, "maturity_date": (datetime.now() + timedelta(days=fd_tenure*30)).strftime("%Y-%m-%d")}
                    elif acc_type == "Systematic Investment Plan (SIP)":
                        metadata = {"sip_amount": sip_monthly, "months": sip_months, "next_due": datetime.now().strftime("%Y-%m-%d")}
                    cursor.execute("INSERT INTO accounts (user_id, account_type, account_number, balance, metadata) VALUES (?,?,?,?,?)",
                                   (st.session_state.user_id, acc_type, acc_num, init_deposit, str(metadata)))
                    conn.commit()
                    st.success(f"{acc_type} opened! Account number: {acc_num}")
                conn.close()
                st.rerun()
        
        st.subheader("📋 Your Accounts")
        accounts = get_user_accounts()
        for _, acc in accounts.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([2,1,1])
                with col1:
                    st.markdown(f"### {acc['account_type']}\n`{acc['account_number']}`")
                    if acc['account_type'] in ['Fixed Deposit (FD)', 'Systematic Investment Plan (SIP)']:
                        meta = eval(acc['metadata']) if acc['metadata'] else {}
                        if acc['account_type'] == 'Fixed Deposit (FD)':
                            st.caption(f"🏦 Tenure: {meta.get('tenure_months', 'N/A')} months @ {meta.get('interest_rate', 7.5)}%")
                            st.caption(f"📅 Maturity: {meta.get('maturity_date', 'N/A')}")
                        else:
                            st.caption(f"💰 Monthly SIP: ₹{meta.get('sip_amount', 0):,.2f} for {meta.get('months', 0)} months")
                with col2:
                    st.metric("Balance", f"₹{acc['balance']:,.2f}")
                with col3:
                    if acc['account_type'] in ['Savings','Current']:
                        st.success("Active")
                    else:
                        st.info("Investment Account")
                if st.button("🗑️ Delete", key=f"del_acc_{acc['id']}"):
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    if acc['balance'] > 0:
                        st.error("Cannot delete account with positive balance. Please withdraw all funds first.")
                    else:
                        cursor.execute("DELETE FROM accounts WHERE id = ? AND user_id = ?", (acc['id'], st.session_state.user_id))
                        conn.commit()
                        st.success(f"Account {acc['account_number']} deleted.")
                        st.rerun()
                    conn.close()
                st.markdown("---")
    
    # ---------- MONEY TRANSFER ----------
    elif selected == "Money Transfer":
        st.title("💰 Money Transfer")
        accounts = get_user_accounts()
        transferrable = accounts[accounts['account_type'].isin(['Savings','Current'])]
        if len(transferrable)==0:
            st.warning("You need a Savings or Current account to transfer money")
        else:
            source_opts = {f"{row['account_type']} - {row['account_number']} (₹{row['balance']:,.2f})": row['id'] for _, row in transferrable.iterrows()}
            source_label = st.selectbox("Source Account", list(source_opts.keys()))
            src_id = source_opts[source_label]
            src_balance = transferrable[transferrable['id']==src_id]['balance'].values[0]
            src_account_number = transferrable[transferrable['id']==src_id]['account_number'].values[0]
            
            with st.expander("📱 Your Receiving QR Code (Share with sender)"):
                qr_img = generate_qr_code(src_account_number)
                if qr_img:
                    buf = io.BytesIO()
                    qr_img.save(buf, format="PNG")
                    buf.seek(0)
                    st.image(buf, width=200)
                    st.download_button("Download QR Code", data=buf, file_name=f"receive_qr_{src_account_number}.png", mime="image/png")
            
            amount = st.number_input("Amount (₹)", min_value=1.0, max_value=src_balance, step=100.0)
            
            st.markdown("### Scan Recipient QR Code")
            scan_method = st.radio("Choose method", ["Upload QR Image", "Use Camera (Live)"])
            recipient_acc = None
            
            if scan_method == "Upload QR Image":
                qr_file = st.file_uploader("Upload QR Code", type=['png','jpg','jpeg'])
                if qr_file:
                    decoded = decode_qr_code(qr_file)
                    if decoded:
                        st.success(f"Decoded: {decoded}")
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM accounts WHERE account_number = ?", (decoded,))
                        acc_data = cursor.fetchone()
                        conn.close()
                        if acc_data and acc_data[0] != src_id:
                            recipient_acc = acc_data[0]
                            st.success("Recipient account found!")
                        else:
                            st.error("Invalid QR code (self or not found)")
            else:
                camera_photo = st.camera_input("Take a photo of the QR code")
                if camera_photo:
                    decoded = decode_qr_code(camera_photo)
                    if decoded:
                        st.success(f"Decoded: {decoded}")
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM accounts WHERE account_number = ?", (decoded,))
                        acc_data = cursor.fetchone()
                        conn.close()
                        if acc_data and acc_data[0] != src_id:
                            recipient_acc = acc_data[0]
                            st.success("Recipient account found!")
                        else:
                            st.error("Invalid QR code")
                    else:
                        st.error("Could not decode QR from camera image.")
            
            manual_acc = st.text_input("Or enter account number manually")
            if manual_acc:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM accounts WHERE account_number = ?", (manual_acc,))
                acc_data = cursor.fetchone()
                conn.close()
                if acc_data and acc_data[0] != src_id:
                    recipient_acc = acc_data[0]
            
            if st.button("Transfer", type="primary"):
                if recipient_acc and amount>0:
                    is_fraud, score = fraud_detector.predict_transaction_fraud(st.session_state.user_id, src_id, recipient_acc, amount)
                    if is_fraud:
                        st.markdown(f'<div class="alert-danger">⚠️ HIGH FRAUD RISK (Score: {score:.2f})! Transaction blocked.</div>', unsafe_allow_html=True)
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO transactions (from_account_id, to_account_id, amount, timestamp, type, status, fraud_score) VALUES (?,?,?,?,?,?,?)",
                                       (src_id, recipient_acc, amount, datetime.now(), 'transfer', 'blocked', score))
                        tx_id = cursor.lastrowid
                        cursor.execute("INSERT INTO fraud_alerts (transaction_id, alert_message, timestamp, reviewed) VALUES (?,?,?,?)",
                                       (tx_id, f"BLOCKED transfer: ₹{amount} from {src_account_number} due to fraud score {score:.2f}", datetime.now(), 0))
                        conn.commit()
                        conn.close()
                    else:
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        try:
                            cursor.execute("BEGIN TRANSACTION")
                            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, src_id))
                            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, recipient_acc))
                            cursor.execute("INSERT INTO transactions (from_account_id, to_account_id, amount, timestamp, type, status, fraud_score) VALUES (?,?,?,?,?,?,?)",
                                           (src_id, recipient_acc, amount, datetime.now(), 'transfer', 'completed', score))
                            tx_id = cursor.lastrowid
                            if score > 0.7:
                                cursor.execute("INSERT INTO fraud_alerts (transaction_id, alert_message, timestamp, reviewed) VALUES (?,?,?,?)",
                                               (tx_id, f"Suspicious transfer ₹{amount} from {src_account_number} (score {score:.2f})", datetime.now(), 0))
                                st.warning(f"⚠️ Fraud score {score:.2f} - transaction flagged.")
                            conn.commit()
                            st.success(f"✅ Transferred ₹{amount:,.2f} successfully!")
                            st.balloons()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Transfer failed: {e}")
                        finally:
                            conn.close()
                            st.rerun()
                else:
                    st.warning("Please specify recipient and valid amount")
    
    # ---------- TRANSACTION HISTORY ----------
    elif selected == "Transaction History":
        st.title("📜 Transaction History")
        accounts = get_user_accounts()
        acc_opts = {f"{row['account_type']} - {row['account_number']}": row['id'] for _, row in accounts.iterrows()}
        chosen = st.selectbox("Select Account", list(acc_opts.keys()))
        acc_id = acc_opts[chosen]
        conn = db.get_connection()
        txns = pd.read_sql_query("""
            SELECT t.id, t.amount, t.timestamp, t.type, t.status, t.fraud_score,
                   a1.account_number as from_account, a2.account_number as to_account
            FROM transactions t
            LEFT JOIN accounts a1 ON t.from_account_id = a1.id
            LEFT JOIN accounts a2 ON t.to_account_id = a2.id
            WHERE t.from_account_id = ? OR t.to_account_id = ?
            ORDER BY t.timestamp DESC
        """, conn, params=(acc_id, acc_id))
        conn.close()
        if len(txns)==0: st.info("No transactions")
        else:
            st.dataframe(txns[['timestamp','type','amount','from_account','to_account','status','fraud_score']], use_container_width=True,
                         column_config={"amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
                                        "fraud_score": st.column_config.ProgressColumn("Fraud Score", format="%.2f", min_value=0, max_value=1)})
    
    # ---------- ACCOUNT STATEMENTS (User) ----------
    elif selected == "Account Statements":
        st.title("📄 Account Statements")
        accounts = get_user_accounts()
        acc_opts = {f"{row['account_type']} - {row['account_number']}": row['id'] for _, row in accounts.iterrows()}
        chosen = st.selectbox("Select Account", list(acc_opts.keys()))
        acc_id = acc_opts[chosen]
        col1,col2 = st.columns(2)
        with col1: start = st.date_input("From", datetime.now().date().replace(day=1))
        with col2: end = st.date_input("To", datetime.now().date())
        if st.button("Generate Statement"):
            conn = db.get_connection()
            df = pd.read_sql_query("""
                SELECT t.timestamp, t.type, t.amount, a1.account_number as from_acc, a2.account_number as to_acc, t.status
                FROM transactions t
                LEFT JOIN accounts a1 ON t.from_account_id = a1.id
                LEFT JOIN accounts a2 ON t.to_account_id = a2.id
                WHERE (t.from_account_id = ? OR t.to_account_id = ?) AND DATE(t.timestamp) BETWEEN ? AND ?
                ORDER BY t.timestamp
            """, conn, params=(acc_id, acc_id, start, end))
            conn.close()
            if len(df)==0: st.warning("No transactions in this period")
            else:
                st.dataframe(df)
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv, file_name=f"statement_{start}_{end}.csv")
    
    # ---------- PROFILE ----------
    elif selected == "Profile":
        st.title("👤 My Profile")
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, email, pan, photo_path FROM users WHERE id = ?", (st.session_state.user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            col1, col2 = st.columns([1,2])
            with col1:
                if user[3] and os.path.exists(user[3]): st.image(user[3], width=200)
                else: st.image("https://img.icons8.com/color/96/000000/user.png", width=200)
            with col2:
                st.markdown(f"**Full Name:** {user[0]}\n\n**Email:** {user[1]}\n\n**PAN:** {user[2]}")
        
        st.markdown("---")
        st.subheader("🔐 Change Password")
        with st.form("change_password"):
            old_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password", type="password")
            confirm_new = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                if old_pw and new_pw and confirm_new:
                    if new_pw != confirm_new:
                        st.error("New passwords do not match")
                    else:
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (st.session_state.user_id,))
                        curr_hash = cursor.fetchone()[0]
                        if verify_password(old_pw, curr_hash):
                            new_hash = hash_password(new_pw)
                            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, st.session_state.user_id))
                            conn.commit()
                            st.success("Password changed successfully! Please login again.")
                            logout()
                        else:
                            st.error("Current password is incorrect")
                        conn.close()
                else:
                    st.warning("Please fill all fields")
        
        st.subheader("⚠️ Delete My Account")
        st.warning("This action is irreversible. All your accounts and transactions will be deleted.")
        confirm_text = st.text_input("Type 'DELETE' to confirm account deletion")
        if st.button("Permanently Delete Account", type="primary"):
            if confirm_text == "DELETE":
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transactions WHERE from_account_id IN (SELECT id FROM accounts WHERE user_id=?) OR to_account_id IN (SELECT id FROM accounts WHERE user_id=?)",
                               (st.session_state.user_id, st.session_state.user_id))
                cursor.execute("DELETE FROM accounts WHERE user_id = ?", (st.session_state.user_id,))
                cursor.execute("DELETE FROM users WHERE id = ?", (st.session_state.user_id,))
                conn.commit()
                conn.close()
                st.success("Account deleted. You will be logged out.")
                logout()
            else:
                st.error("Please type DELETE to confirm")
    
    # ==================== ADMIN SECTIONS ====================
    
    # ---------- ADMIN DASHBOARD (Enhanced with Analytics & User Management) ----------
    elif selected == "Admin Dashboard" and st.session_state.is_admin:
        st.title("👑 Admin Dashboard")
        
        # Fetch data
        conn = db.get_connection()
        users_df = pd.read_sql_query("SELECT id, full_name, email, pan, created_at FROM users WHERE is_admin = 0", conn)
        accounts_df = pd.read_sql_query("SELECT a.id, a.user_id, a.account_type, a.account_number, a.balance, u.full_name FROM accounts a JOIN users u ON a.user_id = u.id", conn)
        transactions_df = pd.read_sql_query("SELECT t.id, t.amount, t.timestamp, t.type, t.status, u.full_name as user_name FROM transactions t LEFT JOIN accounts a ON t.from_account_id = a.id LEFT JOIN users u ON a.user_id = u.id", conn)
        fraud_df = pd.read_sql_query("SELECT fa.id, fa.alert_message, fa.timestamp, fa.reviewed, u.full_name FROM fraud_alerts fa JOIN transactions t ON fa.transaction_id = t.id LEFT JOIN accounts a ON t.from_account_id = a.id LEFT JOIN users u ON a.user_id = u.id", conn)
        conn.close()
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🚨 Fraud Alerts", "📈 Analytics", "👥 User Management"])
        
        # ----- Tab 1: Overview -----
        with tab1:
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Total Users", len(users_df))
            with col2: st.metric("Total Accounts", len(accounts_df))
            with col3: st.metric("Total Transactions", len(transactions_df))
            with col4: st.metric("Pending Fraud Alerts", len(fraud_df[fraud_df['reviewed']==0]))
            
            st.subheader("Recent Transactions")
            recent = transactions_df.head(10)
            st.dataframe(recent[['timestamp', 'user_name', 'amount', 'type', 'status']], use_container_width=True)
        
        # ----- Tab 2: Fraud Alerts -----
        with tab2:
            if len(fraud_df)==0:
                st.info("No fraud alerts")
            else:
                for _, alert in fraud_df.iterrows():
                    with st.expander(f"Alert #{alert['id']} - {alert['timestamp']}"):
                        st.write(f"**User:** {alert['full_name']}")
                        st.write(f"**Message:** {alert['alert_message']}")
                        if not alert['reviewed']:
                            if st.button("Mark Reviewed", key=f"rev_{alert['id']}"):
                                conn = db.get_connection()
                                conn.execute("UPDATE fraud_alerts SET reviewed = 1 WHERE id = ?", (alert['id'],))
                                conn.commit()
                                conn.close()
                                st.rerun()
        
        # ----- Tab 3: Analytics (Now functional) -----
        with tab3:
            st.subheader("Transaction Trends")
            if len(transactions_df) > 0:
                # Daily transaction volume
                txns_daily = transactions_df.copy()
                txns_daily['date'] = pd.to_datetime(txns_daily['timestamp']).dt.date
                daily_volume = txns_daily.groupby('date')['amount'].sum().reset_index()
                fig1 = px.line(daily_volume, x='date', y='amount', title='Daily Transaction Volume (₹)')
                st.plotly_chart(fig1, use_container_width=True)
                
                # Transaction type distribution
                type_dist = transactions_df['type'].value_counts().reset_index()
                type_dist.columns = ['Type', 'Count']
                fig2 = px.pie(type_dist, values='Count', names='Type', title='Transaction Types')
                st.plotly_chart(fig2, use_container_width=True)
                
                # Fraud score distribution (if any)
                if 'fraud_score' in transactions_df.columns:
                    fig3 = px.histogram(transactions_df, x='fraud_score', nbins=20, title='Fraud Score Distribution')
                    st.plotly_chart(fig3, use_container_width=True)
                
                # Account balance distribution
                balance_dist = accounts_df['balance'].value_counts(bins=10).reset_index()
                fig4 = px.bar(accounts_df, x='account_type', y='balance', title='Balance by Account Type', color='account_type')
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("Not enough data for analytics yet.")
        
        # ----- Tab 4: User Management (All users & accounts + Deposit/Withdraw) -----
        with tab4:
            st.subheader("All Users and Their Accounts")
            # Display all users with their accounts
            all_users_data = []
            conn = db.get_connection()
            users_all = pd.read_sql_query("SELECT id, full_name, email, pan FROM users WHERE is_admin = 0", conn)
            for _, user in users_all.iterrows():
                user_accounts = pd.read_sql_query("SELECT account_type, account_number, balance FROM accounts WHERE user_id = ?", conn, params=(user['id'],))
                for _, acc in user_accounts.iterrows():
                    all_users_data.append({
                        'User ID': user['id'],
                        'Name': user['full_name'],
                        'Email': user['email'],
                        'PAN': user['pan'],
                        'Account Type': acc['account_type'],
                        'Account Number': acc['account_number'],
                        'Balance (₹)': acc['balance']
                    })
            conn.close()
            
            if all_users_data:
                df_users_accounts = pd.DataFrame(all_users_data)
                st.dataframe(df_users_accounts, use_container_width=True)
            else:
                st.info("No users found.")
            
            st.markdown("---")
            st.subheader("💰 Admin Deposit / Withdraw")
            st.write("Perform deposit or withdrawal on any user's account.")
            
            # Select user and account
            conn = db.get_connection()
            users_list = pd.read_sql_query("SELECT id, full_name, email FROM users WHERE is_admin = 0", conn)
            user_options = {f"{row['full_name']} ({row['email']})": row['id'] for _, row in users_list.iterrows()}
            selected_user = st.selectbox("Select User", list(user_options.keys()))
            user_id = user_options[selected_user]
            
            accounts_list = pd.read_sql_query("SELECT id, account_number, account_type, balance FROM accounts WHERE user_id = ?", conn, params=(user_id,))
            conn.close()
            if len(accounts_list) == 0:
                st.warning("This user has no accounts.")
            else:
                acc_options = {f"{row['account_type']} - {row['account_number']} (₹{row['balance']:,.2f})": row['id'] for _, row in accounts_list.iterrows()}
                selected_acc = st.selectbox("Select Account", list(acc_options.keys()))
                account_id = acc_options[selected_acc]
                current_balance = accounts_list[accounts_list['id'] == account_id]['balance'].values[0]
                
                operation = st.radio("Operation", ["Deposit", "Withdraw"])
                amount = st.number_input("Amount (₹)", min_value=0.01, step=100.0)
                
                if st.button("Execute Transaction"):
                    if operation == "Deposit":
                        new_balance = current_balance + amount
                        # Update account
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
                        # Record transaction (admin deposit from dummy system account)
                        dummy_account = "ADMIN000"
                        cursor.execute("INSERT INTO transactions (from_account_id, to_account_id, amount, timestamp, type, status, fraud_score) VALUES (?,?,?,?,?,?,?)",
                                       (None, account_id, amount, datetime.now(), 'admin_deposit', 'completed', 0.0))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Deposited ₹{amount:,.2f} to account. New balance: ₹{new_balance:,.2f}")
                        st.rerun()
                    else:  # Withdraw
                        if amount > current_balance:
                            st.error("Insufficient balance for withdrawal.")
                        else:
                            new_balance = current_balance - amount
                            conn = db.get_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
                            cursor.execute("INSERT INTO transactions (from_account_id, to_account_id, amount, timestamp, type, status, fraud_score) VALUES (?,?,?,?,?,?,?)",
                                           (account_id, None, amount, datetime.now(), 'admin_withdraw', 'completed', 0.0))
                            conn.commit()
                            conn.close()
                            st.success(f"✅ Withdrew ₹{amount:,.2f} from account. New balance: ₹{new_balance:,.2f}")
                            st.rerun()
    
    # ---------- EMPLOYEE MANAGEMENT ----------
    elif selected == "Employee Management" and st.session_state.is_admin:
        st.title("👥 Employee Management")
        with st.expander("➕ Add New Employee"):
            with st.form("add_employee"):
                emp_name = st.text_input("Full Name")
                emp_role = st.selectbox("Role", ["Branch Manager", "Loan Officer", "Customer Support", "IT Staff", "Accountant", "Other"])
                emp_email = st.text_input("Email")
                emp_phone = st.text_input("Phone")
                emp_join = st.date_input("Join Date", datetime.now().date())
                emp_salary = st.number_input("Monthly Salary (₹)", min_value=0.0, step=1000.0)
                submitted = st.form_submit_button("Add Employee")
                if submitted:
                    if emp_name and emp_email:
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        try:
                            cursor.execute("INSERT INTO employees (name, role, email, phone, join_date, salary) VALUES (?,?,?,?,?,?)",
                                           (emp_name, emp_role, emp_email, emp_phone, emp_join, emp_salary))
                            conn.commit()
                            st.success(f"Employee {emp_name} added!")
                        except sqlite3.IntegrityError:
                            st.error("Email already exists")
                        finally:
                            conn.close()
                    else:
                        st.warning("Name and email required")
        
        st.subheader("📋 Employee List")
        conn = db.get_connection()
        employees = pd.read_sql_query("SELECT id, name, role, email, phone, join_date, salary FROM employees ORDER BY join_date DESC", conn)
        conn.close()
        if len(employees)==0:
            st.info("No employees found")
        else:
            edited = st.data_editor(employees, use_container_width=True, num_rows="dynamic", key="emp_editor")
            if st.button("Save Changes"):
                conn = db.get_connection()
                cursor = conn.cursor()
                for _, row in edited.iterrows():
                    cursor.execute("UPDATE employees SET name=?, role=?, email=?, phone=?, join_date=?, salary=? WHERE id=?",
                                   (row['name'], row['role'], row['email'], row['phone'], row['join_date'], row['salary'], row['id']))
                conn.commit()
                conn.close()
                st.success("Employee data updated!")
                st.rerun()
            del_id = st.number_input("Employee ID to delete", min_value=0, step=1)
            if st.button("Delete Employee"):
                if del_id:
                    conn = db.get_connection()
                    conn.execute("DELETE FROM employees WHERE id = ?", (del_id,))
                    conn.commit()
                    conn.close()
                    st.success(f"Employee {del_id} deleted")
                    st.rerun()
    
    # ---------- BANK STATEMENTS (Admin) ----------
    elif selected == "Bank Statements" and st.session_state.is_admin:
        st.title("🏦 Bank Statements (Admin)")
        conn = db.get_connection()
        users_df = pd.read_sql_query("SELECT id, email, full_name FROM users", conn)
        user_options = {f"{row['full_name']} ({row['email']})": row['id'] for _, row in users_df.iterrows()}
        selected_user = st.selectbox("Select User", list(user_options.keys()))
        user_id = user_options[selected_user]
        accounts_df = pd.read_sql_query("SELECT id, account_type, account_number FROM accounts WHERE user_id = ?", conn, params=(user_id,))
        conn.close()
        if len(accounts_df)==0:
            st.warning("This user has no accounts.")
        else:
            acc_options = {f"{row['account_type']} - {row['account_number']}": row['id'] for _, row in accounts_df.iterrows()}
            selected_acc = st.selectbox("Select Account", list(acc_options.keys()))
            account_id = acc_options[selected_acc]
            col1, col2 = st.columns(2)
            with col1: start_date = st.date_input("From Date", datetime.now().date() - timedelta(days=30))
            with col2: end_date = st.date_input("To Date", datetime.now().date())
            if st.button("Generate Statement"):
                conn = db.get_connection()
                stmt = pd.read_sql_query("""
                    SELECT t.timestamp, t.type, t.amount, 
                           a1.account_number as from_account, a2.account_number as to_account,
                           t.status, t.fraud_score
                    FROM transactions t
                    LEFT JOIN accounts a1 ON t.from_account_id = a1.id
                    LEFT JOIN accounts a2 ON t.to_account_id = a2.id
                    WHERE (t.from_account_id = ? OR t.to_account_id = ?)
                    AND DATE(t.timestamp) BETWEEN ? AND ?
                    ORDER BY t.timestamp
                """, conn, params=(account_id, account_id, start_date, end_date))
                conn.close()
                if len(stmt)==0:
                    st.info("No transactions in this period.")
                else:
                    st.subheader(f"Statement for {selected_acc} ({start_date} to {end_date})")
                    st.dataframe(stmt, use_container_width=True)
                    csv = stmt.to_csv(index=False)
                    st.download_button("Download CSV", csv, file_name=f"admin_statement_{selected_acc}_{start_date}_{end_date}.csv")
    
    # ---------- USER ACCOUNT LOOKUP ----------
    elif selected == "User Account Lookup" and st.session_state.is_admin:
        st.title("🔍 User Account Lookup")
        acc_num = st.text_input("Enter Account Number")
        if st.button("Search"):
            if acc_num:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.id, a.account_type, a.account_number, a.balance, a.created_at,
                           u.id, u.full_name, u.email, u.pan
                    FROM accounts a
                    JOIN users u ON a.user_id = u.id
                    WHERE a.account_number = ?
                """, (acc_num,))
                result = cursor.fetchone()
                conn.close()
                if result:
                    st.success(f"Account found for user: {result[6]}")
                    st.json({
                        "Account Number": result[2],
                        "Type": result[1],
                        "Balance": f"₹{result[3]:,.2f}",
                        "Opened On": result[4],
                        "User Name": result[6],
                        "User Email": result[7],
                        "User PAN": result[8]
                    })
                    conn = db.get_connection()
                    txns = pd.read_sql_query("""
                        SELECT t.timestamp, t.amount, a1.account_number as from_acc, a2.account_number as to_acc, t.status
                        FROM transactions t
                        LEFT JOIN accounts a1 ON t.from_account_id = a1.id
                        LEFT JOIN accounts a2 ON t.to_account_id = a2.id
                        WHERE t.from_account_id = ? OR t.to_account_id = ?
                        ORDER BY t.timestamp DESC LIMIT 10
                    """, conn, params=(result[0], result[0]))
                    conn.close()
                    st.subheader("Recent Transactions")
                    st.dataframe(txns)
                else:
                    st.error("Account number not found")