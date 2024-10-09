from seleniumbase import BaseCase
from seleniumbase import Driver
import time

class PreLoggedInLoginToAmazon(BaseCase):
    def login_amazon_jobs(self):
        # Path to your Chrome profile
        profile_path = "/Users/rushideep/Library/Application Support/Google/Chrome/Default"

        # Create the driver with your Chrome profile and disable undetected mode (since it's not needed here)
        driver = Driver(browser="chrome", user_data_dir=profile_path, uc=False)

        # Step 1: Open the Amazon Jobs login page (session should already be logged in)
        url = "https://www.amazon.jobs/en-US/applicant/login?relay=%2Fen-US%2Fapplicant"
        driver.get(url)

        # Perform any further actions on the Amazon page
        print("Amazon Jobs page opened using the pre-logged-in Chrome profile.")
        input("Press Enter to close the browser...")

        # Close the browser after inspection
        driver.quit()

if __name__ == "__main__":
    PreLoggedInLoginToAmazon().login_amazon_jobs()
