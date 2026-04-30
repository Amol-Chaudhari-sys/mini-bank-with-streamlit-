# models/fraud_detector.py
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os
from datetime import datetime

class FraudDetector:
    def __init__(self, db_manager, model_path="fraud_model.pkl"):
        self.db = db_manager
        self.model_path = model_path
        self.model = None
    
    def extract_features(self, df_transactions):
        """Extract features for fraud detection"""
        if len(df_transactions) == 0:
            return pd.DataFrame()
        
        # Feature engineering
        features = pd.DataFrame()
        features['amount'] = df_transactions['amount']
        features['hour'] = pd.to_datetime(df_transactions['timestamp']).dt.hour
        features['day_of_week'] = pd.to_datetime(df_transactions['timestamp']).dt.dayofweek
        features['amount_log'] = np.log1p(df_transactions['amount'])
        
        # Rolling statistics per account (simplified)
        features['amount_mean_rolling'] = df_transactions['amount'].rolling(window=5, min_periods=1).mean()
        features['amount_std_rolling'] = df_transactions['amount'].rolling(window=5, min_periods=1).std().fillna(0)
        
        return features.fillna(0)
    
    def train_model(self, force_retrain=False):
        """Train Isolation Forest model on historical transactions"""
        if not force_retrain and os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            return
        
        conn = self.db.get_connection()
        # Get all completed transactions
        transactions = pd.read_sql_query(
            "SELECT id, amount, timestamp FROM transactions WHERE status = 'completed' ORDER BY timestamp",
            conn
        )
        conn.close()
        
        if len(transactions) < 10:
            # Generate synthetic data for initial training
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
        """Predict if a transaction is fraudulent"""
        if self.model is None:
            self.train_model()
        
        # Get recent transactions for context
        conn = self.db.get_connection()
        recent_txns = pd.read_sql_query(
            """
            SELECT t.amount, t.timestamp
            FROM transactions t
            WHERE t.from_account_id = ? OR t.to_account_id = ?
            ORDER BY t.timestamp DESC LIMIT 20
            """,
            conn, params=(from_account_id, from_account_id)
        )
        conn.close()
        
        # Create feature for current transaction
        current_time = datetime.now()
        current_df = pd.DataFrame({
            'amount': [amount],
            'timestamp': [current_time]
        })
        
        if len(recent_txns) > 0:
            # Append current to recent for rolling features
            combined = pd.concat([recent_txns, current_df], ignore_index=True)
            features = self.extract_features(combined)
            current_features = features.iloc[[-1]]
        else:
            current_features = self.extract_features(current_df)
        
        # Predict
        prediction = self.model.predict(current_features)[0]
        fraud_score = self.model.score_samples(current_features)[0]
        fraud_prob = 1 / (1 + np.exp(-fraud_score))  # Convert to probability-like score
        
        is_fraud = (prediction == -1) or (fraud_prob > 0.7)
        return is_fraud, float(fraud_prob)
    
    def train_or_load_model(self):
        """Load existing model or train new one"""
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
        else:
            self.train_model()