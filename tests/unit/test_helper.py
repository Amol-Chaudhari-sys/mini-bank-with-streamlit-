# import sys
# import pytest
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# from app import (hash_password, verify_password, validate_pan, validate_name,
#                  generate_account_number, format_currency,
#                  calculate_fd_maturity, calculate_sip_future)

# class TestHelpers:
#     def test_password_hashing(self):
#         pwd = "Secure@123"
#         hashed = hash_password(pwd)
#         assert len(hashed) == 64
#         assert verify_password(pwd, hashed)
#         assert not verify_password("wrong", hashed)

#     def test_pan_validation(self):
#         assert validate_pan("ABCDE1234F") is True
#         assert validate_pan("abcde1234f") is False
#         assert validate_pan("ABCDE1234") is False

#     def test_name_validation(self):
#         assert validate_name("John Doe") is True
#         assert validate_name("John123") is False

#     def test_account_number_generation(self):
#         assert len(generate_account_number()) == 12
#         assert generate_account_number().isdigit()

#     def test_currency_formatting(self):
#         assert format_currency(1234.5) == "₹1,234.50"

#     def test_fd_calculation(self):
#         maturity = calculate_fd_maturity(10000, 12, 7.5)
#         assert round(maturity, 2) == pytest.approx(10771.35, rel=1e-2)

#     def test_sip_calculation(self):
#         future = calculate_sip_future(1000, 12, 12)
#         assert round(future, 2) == pytest.approx(12709.46, rel=1e-2)