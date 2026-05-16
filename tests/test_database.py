import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
from app import DatabaseManager

def test_user_creation():
    db = DatabaseManager("test.db")
    db.initialize_database()

    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO users (email, password_hash, full_name, pan) VALUES (?, ?, ?, ?)",
                   ("test@test.com", "hash", "Test User", "ABCDE1234Z"))
    
    conn.commit()

    cursor.execute("SELECT * FROM users WHERE email=?", ("test@test.com",))
    user = cursor.fetchone()

    conn.close()

    assert user is not None