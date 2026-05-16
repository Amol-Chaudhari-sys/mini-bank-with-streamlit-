import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import DatabaseManager

def test_transaction_flow():
    db = DatabaseManager("test.db")
    db.initialize_database()

    conn = db.get_connection()
    cursor = conn.cursor()

    # Create users
    cursor.execute("INSERT INTO users (email, password_hash, full_name, pan) VALUES (?,?,?,?)",
                   ("u1@test.com", "hash", "User One", "AAAAA1111A"))
    user1 = cursor.lastrowid

    cursor.execute("INSERT INTO users (email, password_hash, full_name, pan) VALUES (?,?,?,?)",
                   ("u2@test.com", "hash", "User Two", "BBBBB2222B"))
    user2 = cursor.lastrowid

    # Create accounts
    cursor.execute("INSERT INTO accounts (user_id, account_type, account_number, balance) VALUES (?,?,?,?)",
                   (user1, "Savings", "111111111111", 10000))
    acc1 = cursor.lastrowid

    cursor.execute("INSERT INTO accounts (user_id, account_type, account_number, balance) VALUES (?,?,?,?)",
                   (user2, "Savings", "222222222222", 5000))
    acc2 = cursor.lastrowid

    # Transfer
    cursor.execute("UPDATE accounts SET balance = balance - 1000 WHERE id=?", (acc1,))
    cursor.execute("UPDATE accounts SET balance = balance + 1000 WHERE id=?", (acc2,))

    conn.commit()

    cursor.execute("SELECT balance FROM accounts WHERE id=?", (acc1,))
    new_balance = cursor.fetchone()[0]

    conn.close()

    assert new_balance == 9000