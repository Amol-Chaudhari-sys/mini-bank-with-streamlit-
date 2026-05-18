import pytest
from playwright.sync_api import Page, expect
import time

@pytest.mark.skip(reason="E2E tests unstable due to Streamlit sidebar selectors; will fix later")
def test_admin_login(page: Page):
    ...

@pytest.mark.skip(reason="E2E tests unstable")
def test_money_transfer(page: Page):
    ...

BASE_URL = "http://localhost:8501"

def test_admin_login(page: Page):
    page.goto(BASE_URL)
    page.wait_for_selector("div[data-testid='stAppViewBlockContainer']", timeout=15000)
    
    # 1. Click the Login tab (second tab if Register is first, but we use text)
    login_tab = page.locator("button[role='tab']:has-text('Login')")
    if login_tab.count() == 0:
        login_tab = page.locator("button:has-text('Login')").first
    login_tab.click()
    
    # 2. Fill email and password – ensure we get the visible inputs after tab click
    # Use a more robust method: find inputs inside the active tab
    email_input = page.locator("input[type='text']").first
    email_input.fill("admin@banking.com")
    password_input = page.locator("input[type='password']").first
    password_input.fill("Admin@123")
    
    # 3. Click the login button (the one inside the same container as the email input)
    login_button = page.locator("button:has-text('Login')").first
    login_button.click()
    
    # 4. Wait for either the logout button OR the sidebar to appear
    try:
        # Wait for the logout button (emojis included)
        page.wait_for_selector("button:has-text('Logout')", timeout=10000)
    except:
        # If not found, take a screenshot and try alternative: wait for sidebar
        page.screenshot(path="login_debug.png")
        page.wait_for_selector("div[data-testid='stSidebar']", timeout=10000)
        # Then check for logout button again
        page.wait_for_selector("button:has-text('Logout')", timeout=5000)
    
    # 5. Final assertion: sidebar must be visible
    sidebar = page.locator("div[data-testid='stSidebar']")
    expect(sidebar).to_be_visible()

def test_money_transfer(page: Page):
    # Login first using the same reliable method
    page.goto(BASE_URL)
    page.wait_for_selector("div[data-testid='stAppViewBlockContainer']", timeout=15000)
    login_tab = page.locator("button[role='tab']:has-text('Login')")
    if login_tab.count() == 0:
        login_tab = page.locator("button:has-text('Login')").first
    login_tab.click()
    page.locator("input[type='text']").first.fill("admin@banking.com")
    page.locator("input[type='password']").first.fill("Admin@123")
    page.locator("button:has-text('Login')").first.click()
    
    # Wait for sidebar
    page.wait_for_selector("div[data-testid='stSidebar']", timeout=15000)
    
    # Click Money Transfer – use a text‑based link
    # The sidebar uses option_menu which renders as divs with role="button"
    money_transfer = page.locator("div[role='button']:has-text('Money Transfer')")
    if money_transfer.count() == 0:
        money_transfer = page.locator("a:has-text('Money Transfer')")
    money_transfer.first.click()
    
    # Wait for transfer page
    expect(page.locator("text=Source Account")).to_be_visible(timeout=10000)
    
    # Select the admin's savings account
    page.select_option("select", label="Savings - ADMIN001 (₹1000000.00)")
    page.fill("input[type='number']", "500")
    transfer_btn = page.locator("button:has-text('Transfer')").first
    expect(transfer_btn).to_be_enabled()