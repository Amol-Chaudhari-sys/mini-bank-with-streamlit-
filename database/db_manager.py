# database/db_manager.py
import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path="banking.db"):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def initialize_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
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
        
        # Accounts table
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
        
        # Transactions table
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
        
        # Fraud alerts table
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
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_from ON transactions(from_account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_to ON transactions(to_account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)")
        
        # Check if admin exists, if not create default admin
        cursor.execute("SELECT id FROM users WHERE is_admin = 1")
        if not cursor.fetchone():
            from utils.helpers import hash_password
            admin_pw = hash_password("Admin@123")
            cursor.execute("""
                INSERT INTO users (email, password_hash, full_name, pan, photo_path, is_admin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("admin@banking.com", admin_pw, "System Admin", "ADMIN9999A", "", 1))
            
            # Create admin account
            cursor.execute("SELECT id FROM users WHERE email = 'admin@banking.com'")
            admin_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO accounts (user_id, account_type, account_number, balance)
                VALUES (?, ?, ?, ?)
            """, (admin_id, "Savings", "ADMIN001", 1000000))
        
        conn.commit()
        conn.close()