# models/transaction.py
from datetime import datetime

class TransactionModel:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_transaction(self, from_account_id, to_account_id, amount, transaction_type, status, fraud_score=0.0):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (from_account_id, to_account_id, amount, timestamp, type, status, fraud_score) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (from_account_id, to_account_id, amount, datetime.now(), transaction_type, status, fraud_score)
        )
        tx_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return tx_id
    
    def get_account_transactions(self, account_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.amount, t.timestamp, t.type, t.status, t.fraud_score,
                   a1.account_number as from_account, a2.account_number as to_account
            FROM transactions t
            LEFT JOIN accounts a1 ON t.from_account_id = a1.id
            LEFT JOIN accounts a2 ON t.to_account_id = a2.id
            WHERE t.from_account_id = ? OR t.to_account_id = ?
            ORDER BY t.timestamp DESC
        """, (account_id, account_id))
        transactions = cursor.fetchall()
        conn.close()
        return transactions
    
    def create_fraud_alert(self, transaction_id, alert_message):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO fraud_alerts (transaction_id, alert_message, timestamp, reviewed) VALUES (?, ?, ?, ?)",
            (transaction_id, alert_message, datetime.now(), 0)
        )
        conn.commit()
        conn.close()