import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import hash_password, verify_password, validate_pan, validate_name, calculate_fd_maturity, calculate_sip_future

def test_password_hash():
    pw = "Test@123"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed)

def test_pan_validation():
    assert validate_pan("ABCDE1234F") == True
    assert validate_pan("123INVALID") == False

def test_name_validation():
    assert validate_name("Amol Chaudhari") == True
    assert validate_name("Amol123") == False

def test_fd_calculation():
    result = calculate_fd_maturity(10000, 12)
    assert result > 10000

def test_sip_calculation():
    result = calculate_sip_future(1000, 12)
    assert result > 12000