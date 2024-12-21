import yaml
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from amazon import AmazonJobApplier

# Load configuration from YAML file
def load_yaml_config(config_path):
    print(f"Loading YAML configuration from {config_path}...")
    with open(config_path, "r") as ymlfile:
        config = yaml.safe_load(ymlfile)
    print("YAML configuration loaded successfully.")
    return config

# Initialize the browser with Chrome WebDriver
def init_browser():
    print("Initializing WebDriver...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.implicitly_wait(10)  # Add implicit wait for loading elements
    print("WebDriver initialized successfully.")
    return driver

# Validate the loaded YAML parameters (basic checks)
def validate_yaml(parameters):
    required_fields = ['email', 'password', 'amazon_url', 'positions', 'locations']
    for field in required_fields:
        if field not in parameters:
            raise ValueError(f"Missing required field in configuration: {field}")
    return parameters

if __name__ == '__main__':
    # Load the configuration from YAML
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, '.github', 'workflows', 'config.yml')
    config = load_yaml_config(config_path)

    # Validate the loaded configuration
    parameters = {
        'email': config['credentials']['email'],
        'password': config['credentials']['password'],
        'amazon_url': config['credentials']['amazon_url'],
        # 'amazon_job_search_url': config['credentials']['amazon_job_search_url'],
        'positions': config['job_search']['positions'],
        'locations': config['job_search']['locations'],
        'contact': config['contact'],  # This ensures 'contact' is a dictionary
        'experience': config['experience'],  # This ensures 'experience' is a dictionary
    }
    validate_yaml(parameters)

    # Initialize the browser
    browser = init_browser()

    # Create an instance of AmazonJobApplier and perform login and search
    bot = AmazonJobApplier(parameters, browser)
    bot.login()
    bot.search_jobs()

    # Keep the browser open for inspection
    input("Press Enter to close the browser...")

    # Close the browser after pressing Enter
    print("Closing browser...")
    browser.quit()
    print("Browser closed.")
