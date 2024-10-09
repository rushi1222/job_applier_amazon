import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import shutil

# Path to your default Chrome profile
chrome_profile_path = "/Users/rushideep/Library/Application Support/Google/Chrome"

# Set Chrome options to use the default profile and remove automation warning
chrome_options = Options()
chrome_options.add_argument(f"user-data-dir={chrome_profile_path}")  # Use the default profile
chrome_options.add_argument("profile-directory=Default")  # Specify the default Chrome profile
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Hide automation info bar
chrome_options.add_experimental_option("useAutomationExtension", False)
chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_argument("--no-sandbox")

# Initialize WebDriver with Service object and ChromeDriverManager
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Step 1: Open the Amazon Jobs login page
driver.get("https://www.amazon.jobs/en-US/applicant/login?relay=%2Fen-US%2Fapplicant")

# Step 2: Click the "Accept All" button using text within the <b> tag
try:
    accept_cookies_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[.//b[contains(text(), 'Accept all')]]"))
    )
    accept_cookies_button.click()
    print("Cookies accepted successfully.")
except Exception as e:
    print(f"Failed to click the Accept All button: {e}")

# Wait for a few seconds before proceeding to the next step
time.sleep(5)

# Step 3: Click the "Login with Google" link using its text
try:
    google_login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Login with Google')]"))
    )
    google_login_button.click()
    print("Login with Google clicked successfully.")
except Exception as e:
    print(f"Failed to click the Login with Google button: {e}")

# Step 4: Enter email and click Next
try:
    # Wait for the email input field to appear
    email_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
    )
    email_input.send_keys("k.saraswathi1222@gmail.com")
    print("Email entered successfully.")

    # Click the "Next" button using its text
    next_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Next')]/.."))
    )
    next_button.click()
    print("Next button clicked.")
except Exception as e:
    print(f"Failed to enter email or click Next: {e}")

# Keep the browser open for inspection
input("Press Enter to close the browser...")

# Close the browser
driver.quit()

# Optionally, delete the temporary profile directory after use
shutil.rmtree(chrome_profile_path)
