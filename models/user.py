# models/user.py
import hashlib

class UserModel:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def create_user(self, email, password_hash, full_name, pan, photo_path, is_admin=0):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, full_name, pan, photo_path, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
            (email, password_hash, full_name, pan, photo_path, is_admin)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    
    def get_user_by_email(self, email):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash, full_name, pan, photo_path, is_admin FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def get_user_by_id(self, user_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, full_name, pan, photo_path, is_admin FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user