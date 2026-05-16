# import sys
# import sqlite3
# from pathlib import Path  # ⬅️ ADD THIS IMPORT
# import pytest

# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# from app import DatabaseManager

# class TestAccountManagement:
#     @pytest.fixture
#     def db_conn(self):
#         conn = sqlite3.connect(":memory:")
#         # Create minimal schema
#         cursor = conn.cursor()
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS accounts (
#                 id INTEGER PRIMARY KEY,
#                 user_id INTEGER,
#                 account_number TEXT UNIQUE,
#                 account_type TEXT,
#                 balance REAL,
#                 metadata TEXT
#             )
#         """)
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS transactions (
#                 id INTEGER PRIMARY KEY,
#                 from_account_id INTEGER,
#                 to_account_id INTEGER,
#                 amount REAL,
#                 timestamp TEXT,
#                 type TEXT,
#                 status TEXT,
#                 fraud_score REAL
#             )
#         """)
#         yield conn
#         conn.close()

#     def test_create_and_delete_account(self, db_conn):
#         # Generate an account
#         acc_num = "123456789012"
#         cursor = db_conn.cursor()
#         cursor.execute("INSERT INTO accounts (account_number, balance, user_id, account_type) VALUES (?, ?, ?, ?)",
#                        (acc_num, 1000, 1, "Savings"))
#         db_conn.commit()

#         # Verify creation
#         cursor.execute("SELECT * FROM accounts WHERE account_number = ?", (acc_num,))
#         assert cursor.fetchone() is not None

#         # Delete account
#         cursor.execute("DELETE FROM accounts WHERE account_number = ?", (acc_num,))
#         db_conn.commit()
#         cursor.execute("SELECT * FROM accounts WHERE account_number = ?", (acc_num,))
#         assert cursor.fetchone() is None