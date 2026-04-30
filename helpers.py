# utils/helpers.py

import hashlib
import re
import random
import string

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def validate_pan(pan):
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    return bool(re.match(pattern, pan))

def generate_account_number():
    return ''.join(random.choices(string.digits, k=12))

def format_currency(amount):
    return f"₹{amount:,.2f}"