import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from seleniumbase import BaseCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

# Set up logging
logging.basicConfig(filename="amazon_log.log", level=logging.INFO)

class CombinedLoginToAmazon(BaseCase):
    def open_browser_with_profile(self):
        # Path to your default Chrome profile
        chrome_profile_path = "/Users/rushideep/Library/Application Support/Google/Chrome"

        # Set up Chrome options to use the default profile
        chrome_options = Options()
        chrome_options.add_argument(f"user-data-dir={chrome_profile_path}")  # Use default profile
        chrome_options.add_argument("profile-directory=temp_profile")  # Specify the default profile
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Hide automation info bar
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--remote-debugging-port=9223")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")  # Add headless mode for CI

        # Initialize WebDriver using Selenium for loading profile
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        # Step 1: Open the Amazon Jobs login page with Selenium
        self.driver.get("https://www.amazon.jobs/en-US/applicant/login?relay=%2Fen-US%2Fapplicant")
        logging.info("Opened Amazon Jobs with Selenium and Default Chrome profile")

        # Switch to SeleniumBase for further actions
        self.switch_to_seleniumbase()

    def switch_to_seleniumbase(self):
        # Now use SeleniumBase for browser interaction
        self.driver.get("https://www.amazon.jobs/en-US/applicant/login?relay=%2Fen-US%2Fapplicant")
        logging.info("Switched to SeleniumBase for further actions")

        # Step 2: Handle the login process with SeleniumBase
        try:
            accept_cookies_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//b[contains(text(), 'Accept all')]]"))
            )
            accept_cookies_button.click()
            logging.info("Cookies accepted successfully.")
        except Exception as e:
            logging.error(f"Failed to click the Accept All button: {e}")

        # Step 3: Click the "Login with Google" link
        try:
            google_login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Login with Google')]"))
            )
            google_login_button.click()
            logging.info("Login with Google clicked successfully.")
        except Exception as e:
            logging.error(f"Failed to click the Login with Google button: {e}")

        # Step 4: Enter email and click Next
        try:
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
            )
            email_input.send_keys("k.saraswathi1222@gmail.com")
            logging.info("Email entered successfully.")

            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Next')]/.."))
            )
            next_button.click()
            logging.info("Next button clicked.")
        except Exception as e:
            logging.error(f"Failed to enter email or click Next: {e}")

        # Keep the browser open for inspection
        input("Press Enter to close the browser...")

        # Close the browser after inspection
        self.driver.quit()

if __name__ == "__main__":
    CombinedLoginToAmazon().open_browser_with_profile()
