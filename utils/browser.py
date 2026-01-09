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
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    # Basic required flags
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")
    
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
    
    # Use system ChromeDriver if available (for Docker/Cloud Run)
    try:
        # Try to use ChromeDriver from system PATH (installed via chromium-driver package)
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"System ChromeDriver failed, trying ChromeDriverManager: {e}")
        # Fallback to ChromeDriverManager for local development
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.implicitly_wait(10)
    print("WebDriver initialized successfully.")
    return driver
