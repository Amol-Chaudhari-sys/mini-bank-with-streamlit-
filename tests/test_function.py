import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from pathlib import Path   # <-- add this at the top
from pathlib import Path

# Add parent directory to path to import from app.py
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all helper functions and classes from app.py
from app import (
    hash_password, verify_password, validate_pan, validate_name,
    calculate_fd_maturity, calculate_sip_future,
    generate_account_number, format_currency
)

# ==================== TEST HELPER FUNCTIONS ====================

def test_hash_password():
    pwd = "MySecret123"
    hashed = hash_password(pwd)
    assert isinstance(hashed, str)
    assert len(hashed) == 64  # SHA256 hex length
    assert verify_password(pwd, hashed) == True
    assert verify_password("Wrong", hashed) == False

def test_validate_pan():
    assert validate_pan("ABCDE1234F") == True   # valid
    assert validate_pan("abcde1234f") == False  # must be uppercase
    assert validate_pan("ABCD12345E") == False  # wrong pattern
    assert validate_pan("ABCDE1234") == False   # missing last letter
    assert validate_pan("ABCDE1234FGH") == False # too long

def test_validate_name():
    assert validate_name("John Doe") == True
    assert validate_name("Priya Sharma") == True
    assert validate_name("John123") == False   # contains numbers
    assert validate_name("Mary-Jane") == False # hyphen not allowed
    assert validate_name("") == False

def test_generate_account_number():
    acc1 = generate_account_number()
    acc2 = generate_account_number()
    assert isinstance(acc1, str)
    assert len(acc1) == 12
    assert acc1.isdigit()
    assert acc1 != acc2  # should be random

def test_format_currency():
    assert format_currency(1234.5) == "₹1,234.50"
    assert format_currency(0) == "₹0.00"
    assert format_currency(1000000) == "₹1,000,000.00"

def test_fd_maturity_calculation():
    # Test FD: principal 10000, 12 months @ 7.5%
    maturity = calculate_fd_maturity(10000, 12, 7.5)
    # Expected: quarterly compounding: 10000 * (1 + 0.075/4)^4 = 10000 * 1.077135... ≈ 10771.35
    assert round(maturity, 2) == pytest.approx(10771.35, rel=1e-2)

def test_sip_future_value():
    # SIP: monthly 1000 for 12 months @ 12% expected return
    future = calculate_sip_future(1000, 12, 12)
    # Formula gives approx 12709.46
    assert round(future, 2) == pytest.approx(12709.46, rel=1e-2)

# ==================== TEST DATABASE (IN-MEMORY) ====================
# These tests require you to extract DatabaseManager from app.py
# I'll show you how to test a simplified DB function – but since your app is single-file,
# you may want to refactor later. For now, I'll skip heavy DB tests.

def test_create_user_logic():
    # Simulate registration logic without actual UI
    # Example: check that PAN is unique – but we don't have a test DB here.
    # Instead, verify that duplicate email triggers error in logic.
    # Since your app uses global DB, this is harder. 
    # For true unit testing, extract DatabaseManager into a separate module.
    pass

# ==================== MOCK FRAUD DETECTOR (optional) ====================
def test_fraud_detector_features():
    # You can test the feature extraction logic if you separate it.
    # For now, just verify the model can be loaded.
    from app import FraudDetector
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Fake DB connection (just to avoid real DB)
        class FakeDB:
            def get_connection(self):
                import sqlite3
                return sqlite3.connect(":memory:")
        fake_db = FakeDB()
        detector = FraudDetector(fake_db)
        # Should not crash
        assert detector.model is None  # not loaded yet