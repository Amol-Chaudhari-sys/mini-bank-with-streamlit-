import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import tempfile
from app import FraudDetector

class TempDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY, amount REAL, timestamp TEXT, status TEXT, from_account_id INTEGER, to_account_id INTEGER, fraud_score REAL)")
        # Insert a few normal transactions
        import datetime
        now = datetime.datetime.now().isoformat()
        self.conn.execute("INSERT INTO transactions (amount, timestamp, status, from_account_id, to_account_id) VALUES (1000, ?, 'completed', 1, 2)", (now,))
        self.conn.execute("INSERT INTO transactions (amount, timestamp, status, from_account_id, to_account_id) VALUES (2000, ?, 'completed', 1, 2)", (now,))
        self.conn.commit()
    def get_connection(self):
        return self.conn

def test_fraud_prediction():
    db = TempDB()
    detector = FraudDetector(db, model_path="test_model.pkl")
    detector.train_model(force_retrain=True)
    is_fraud, score = detector.predict_transaction_fraud(1, 1, 2, 50000)
    assert isinstance(is_fraud, bool)
    assert 0 <= score <= 1