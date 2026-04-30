# models/account.py
import random
import string

class AccountModel:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def generate_account_number(self):
        return ''.join(random.choices(string.digits, k=12))
    
    def create_account(self, user_id, account_type, account_number, balance, metadata="{}"):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO accounts (user_id, account_type, account_number, balance, metadata) VALUES (?, ?, ?, ?, ?)",
            (user_id, account_type, account_number, balance, metadata)
        )
        account_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return account_id
    
    def get_user_accounts(self, user_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, account_type, account_number, balance, metadata FROM accounts WHERE user_id = ?", (user_id,))
        accounts = cursor.fetchall()
        conn.close()
        return accounts
    
    def get_account_by_number(self, account_number):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, account_type, balance FROM accounts WHERE account_number = ?", (account_number,))
        account = cursor.fetchone()
        conn.close()
        return account
    
    def update_balance(self, account_id, new_balance):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
        conn.commit()
        conn.close()