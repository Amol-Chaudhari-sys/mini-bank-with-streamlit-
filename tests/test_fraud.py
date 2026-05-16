from app import FraudDetector, DatabaseManager
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_fraud_detection():
    db = DatabaseManager("test.db")
    db.initialize_database()

    fraud = FraudDetector(db)
    fraud.train_model(force_retrain=True)

    is_fraud, score = fraud.predict_transaction_fraud(1, 1, 2, 50000)

    assert isinstance(is_fraud, bool)
    assert 0 <= score <= 1