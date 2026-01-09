"""
Helper utilities for debugging and common operations
"""

def space_continue(driver=None, message="Paused for debugging"):
    """
    Pauses execution for debugging purposes.
    
    Args:
        driver: Selenium WebDriver instance (optional) - if provided, shows current URL
        message: Custom message to display (default: "Paused for debugging")
    
    Usage:
        from utils import space_continue
        space_continue(browser, "Check the page state")
    """
    print("\n" + "="*60)
    print(f"🛑 DEBUG PAUSE: {message}")
    if driver:
        try:
            print(f"📍 Current URL: {driver.current_url}")
            print(f"📄 Page Title: {driver.title}")
        except Exception as e:
            print(f"⚠️  Could not fetch page info: {e}")
    print("="*60)
    input("Press Enter to continue...")
    print("▶️  Resuming execution...\n")
