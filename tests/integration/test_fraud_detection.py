# import sys
# import sqlite3
# import tempfile
# import os
# from pathlib import Path

# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# from app import FraudDetector

# class TempFileDB:
#     def __init__(self):
#         self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
#         self._init_db()
    
#     def _init_db(self):
#         conn = sqlite3.connect(self.db_path)
#         cursor = conn.cursor()
#         cursor.execute("""
#             CREATE TABLE transactions (
#                 id INTEGER PRIMARY KEY,
#                 amount REAL,
#                 timestamp TEXT,
#                 status TEXT,
#                 from_account_id INTEGER,
#                 to_account_id INTEGER,
#                 fraud_score REAL
#             )
#         """)
#         cursor.execute("""
#             INSERT INTO transactions (amount, timestamp, status, from_account_id, to_account_id, fraud_score)
#             VALUES (5000, '2025-01-01 10:00:00', 'completed', 1, 2, 0.1)
#         """)
#         conn.commit()
#         conn.close()
    
#     def get_connection(self):
#         return sqlite3.connect(self.db_path)
    
#     def cleanup(self):
#         os.close(self.db_fd)
#         os.unlink(self.db_path)

# def test_fraud_scoring():
#     temp_db = TempFileDB()
#     detector = FraudDetector(temp_db)
#     detector.train_model(force_retrain=True)
#     is_fraud, score = detector.predict_transaction_fraud(1, 1, 2, 50000)
#     assert is_fraud in (True, False)
#     assert 0.0 <= score <= 1.0
#     temp_db.cleanup()