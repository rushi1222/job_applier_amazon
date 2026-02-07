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
    
    # Set Chrome binary for different environments
    chrome_binary_paths = [
        "/usr/bin/google-chrome",        # Standard installation
        "/usr/bin/google-chrome-stable", # Ubuntu/Debian
        "/usr/bin/chromium-browser",     # Chromium
        "/usr/bin/chromium",             # Alternative chromium path
        "/opt/google/chrome/chrome",     # Alternative installation
    ]
    
    for binary_path in chrome_binary_paths:
        if os.path.exists(binary_path):
            chrome_options.binary_location = binary_path
            print(f"Using Chrome binary: {binary_path}")
            break
    
    # Force headless in CI environments
    ci_environment = os.environ.get('GITHUB_ACTIONS') == 'true' or os.environ.get('CI') == 'true'
    if ci_environment and not headless:
        print("⚠️  Forcing headless mode in CI environment")
        headless = True
    
    if headless:
        chrome_options.add_argument("--headless=new")
        print("Running in headless mode")
    
    # Universal Chrome flags (optimized for CI/CD environments)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-automation")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-login-animations")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-default-apps")
    
    # Remove aggressive flags that can cause crashes in CI
    # Removed: --single-process, --no-zygote, --remote-debugging-port
    
    # CI-specific settings
    if ci_environment:
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--max_old_space_size=4096")
        # Memory optimization for CI
        chrome_options.add_argument("--disable-dev-shm-usage")  # Already added above but critical
        chrome_options.add_argument("--js-flags=--max-old-space-size=512")
        chrome_options.add_argument("--aggressive-cache-discard")
        chrome_options.add_argument("--disable-cache")
        chrome_options.add_argument("--disable-application-cache")
        chrome_options.add_argument("--disable-offline-load-stale-cache")
        chrome_options.add_argument("--disk-cache-size=0")
    
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
    
    # Add additional experimental options for stability
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Anti-detection measures for Google and other sophisticated sites
    ci_environment = os.environ.get('GITHUB_ACTIONS') == 'true' or os.environ.get('CI') == 'true'
    if ci_environment:
        # Set realistic user agent for CI
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        # Additional fingerprinting evasion
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2
        })
    
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

    # Configure browser settings for stability
    driver.implicitly_wait(10)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(30)
    
    # Execute script to remove webdriver detection
    try:
        # More robust webdriver property modification
        driver.execute_script("""
            if (navigator.webdriver) {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
            }
        """)
        # Additional stealth measures for sophisticated detection
        driver.execute_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
                configurable: true
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true
            });
        """)
        print("✅ Stealth scripts applied successfully")
    except Exception as e:
        print(f"⚠️  Some stealth scripts failed: {e}")  # Don't fail completely
    
    # Verify browser is responsive
    try:
        driver.execute_script("return document.readyState")
    except Exception as e:
        print(f"⚠️  Browser may not be fully responsive: {e}")
    
    print("✅ WebDriver initialized successfully.")
    return driver