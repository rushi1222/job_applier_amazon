"""
Browser initialization and configuration
"""
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def get_chrome_options(headless=True, download_dir=None):
    """
    Get configured Chrome options
    
    Args:
        headless: Run browser in headless mode (default: True)
        download_dir: Custom download directory path (optional)
    
    Returns:
        Chrome Options object
    """
    chrome_options = Options()
    
    # Set Chrome binary for Docker environments only
    if os.path.exists("/usr/bin/chromium"):
        chrome_options.binary_location = "/usr/bin/chromium"
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    # Universal Chrome flags
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # Configure download directory if specified
    if download_dir:
        os.makedirs(download_dir, exist_ok=True)
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
    
    return chrome_options


def init_browser(headless=True, download_dir=None):
    """
    Initialize Chrome WebDriver with configured options
    
    Args:
        headless: Run browser in headless mode (default: True)
        download_dir: Custom download directory path (optional)
    
    Returns:
        WebDriver instance
    """
    print("Initializing WebDriver...")
    chrome_options = get_chrome_options(headless=headless, download_dir=download_dir)
    
    # Try different ChromeDriver approaches for different environments
    try:
        # First: Try ChromeDriverManager (works great in GitHub Actions)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("WebDriver initialized with ChromeDriverManager")
    except Exception as e1:
        print(f"ChromeDriverManager failed: {e1}")
        try:
            # Second: Try system ChromeDriver (Docker/Cloud environments)
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("WebDriver initialized with system ChromeDriver")
        except Exception as e2:
            print(f"System ChromeDriver failed: {e2}")
            try:
                # Last resort: Auto-detect
                service = Service()
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print("WebDriver initialized with auto-detection")
            except Exception as e3:
                print(f"All ChromeDriver methods failed: {e3}")
                raise e3

    driver.implicitly_wait(10)
    print("WebDriver initialized successfully.")
    return driver
