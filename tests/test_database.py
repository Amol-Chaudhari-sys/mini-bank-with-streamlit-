import sqlite3
import tempfile
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import DatabaseManager, generate_account_number

def test_create_user_and_account():
    # Use a temporary file database (not :memory:)
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    
    db = DatabaseManager(tmp_path)
    db.initialize_database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Insert a test user
    cursor.execute("INSERT INTO users (email, password_hash, full_name, pan, photo_path) VALUES (?,?,?,?,?)",
                   ("test@example.com", "hash", "Test User", "ABCDE1234F", ""))
    user_id = cursor.lastrowid
    
    # Create account
    acc_num = generate_account_number()
    cursor.execute("INSERT INTO accounts (user_id, account_type, account_number, balance) VALUES (?,?,?,?)",
                   (user_id, "Savings", acc_num, 1000))
    conn.commit()
    
    # Verify
    cursor.execute("SELECT balance FROM accounts WHERE account_number = ?", (acc_num,))
    balance = cursor.fetchone()[0]
    assert balance == 1000
    
    conn.close()
    # Clean up
    import os
    os.unlink(tmp_path)