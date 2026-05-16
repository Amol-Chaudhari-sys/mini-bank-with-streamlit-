# import pytest
# from playwright.sync_api import Page, expect
# import subprocess
# import time
# import sys
# import socket

# BASE_URL = "http://localhost:8501"

# def is_port_open(port, host="localhost"):
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#         return s.connect_ex((host, port)) == 0

# class TestBankingE2E:
#     @pytest.fixture(scope="class", autouse=True)
#     def start_app(self):
#         if is_port_open(8501):
#             print("App already running on port 8501, reusing it.")
#             yield
#             return
        
#         process = subprocess.Popen(
#             [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             shell=True,
#             creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
#         )
#         for _ in range(30):
#             if is_port_open(8501):
#                 break
#             time.sleep(1)
#         else:
#             raise RuntimeError("Streamlit app did not start within 30 seconds.")
#         time.sleep(5)
#         yield
#         process.terminate()
#         process.wait()

#     def _login(self, page: Page):
#         """Login helper that switches to the Login tab first."""
#         page.goto(BASE_URL)
#         page.wait_for_selector("div[data-testid='stAppViewBlockContainer']", timeout=15000)
        
#         # 1. Click on the "Login" tab (the first tab, but we use text)
#         login_tab = page.locator("button[data-baseweb='tab']:has-text('Login')").first
#         login_tab.click()
        
#         # 2. Now fill the email and password fields (they belong to the active tab)
#         #    Use more robust selectors
#         email_input = page.locator("input[type='text']").first
#         email_input.fill("admin@banking.com")
        
#         password_input = page.locator("input[type='password']").first
#         password_input.fill("Admin@123")
        
#         # 3. Click the Login button (the first button with the text "Login")
#         login_button = page.locator("button:has-text('Login')").first
#         login_button.click()
        
#         # 4. Wait for the logout button to appear (indicates successful login)
#         page.wait_for_selector("button:has-text('Logout')", timeout=15000)
        
#         # Take a screenshot for debugging if needed
#         page.screenshot(path="after_login_success.png")

#     def test_admin_login(self, page: Page):
#         self._login(page)
#         # Additional checks
#         expect(page.locator("section[data-testid='stSidebar']")).to_be_visible()
#         expect(page.locator("text=Welcome, admin")).to_be_visible()

#     def test_money_transfer_flow(self, page: Page):
#         self._login(page)
        
#         # Click on "Money Transfer" in the sidebar
#         page.locator("a:has-text('Money Transfer')").first.click()
        
#         # Wait for the transfer page
#         expect(page.locator("text=Source Account")).to_be_visible(timeout=10000)
        
#         # Select the source account (admin's savings account)
#         page.select_option("select", label="Savings - ADMIN001 (₹1000000.00)")
        
#         # Enter an amount
#         page.fill("input[type='number']", "500")
        
#         # Verify the Transfer button is enabled
#         transfer_btn = page.locator("button:has-text('Transfer')").first
#         expect(transfer_btn).to_be_enabled()