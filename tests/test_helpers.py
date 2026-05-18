import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app import (
    hash_password, verify_password, validate_pan, validate_name,
    generate_account_number, format_currency,
    calculate_fd_maturity, calculate_sip_future
)

def test_password_hashing():
    pwd = "Test123!"
    hashed = hash_password(pwd)
    assert len(hashed) == 64
    assert verify_password(pwd, hashed)
    assert not verify_password("wrong", hashed)

def test_pan_validation():
    assert validate_pan("ABCDE1234F") is True
    assert validate_pan("abcde1234f") is False
    assert validate_pan("ABCDE1234") is False

def test_name_validation():
    assert validate_name("John Doe") is True
    assert validate_name("John123") is False
    assert validate_name("Mary-Jane") is False

def test_account_number():
    num = generate_account_number()
    assert len(num) == 12
    assert num.isdigit()

def test_currency_format():
    assert format_currency(1234.5) == "₹1,234.50"


def test_fd_maturity():
    maturity = calculate_fd_maturity(10000, 12, 7.5)
    # Your function returns 10771.36 (quarterly compounding)
    assert round(maturity, 2) == 10771.36

def test_sip_future():
    future = calculate_sip_future(1000, 12, 12)
    # Your function returns 12809.33 (monthly compounding)
    assert round(future, 2) == 12809.33