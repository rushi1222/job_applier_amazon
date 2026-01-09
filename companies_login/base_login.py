"""
Base login handler class for all company login implementations
"""

class BaseLogin:
    """Base class for company-specific login handlers"""
    
    def __init__(self, driver, credentials):
        """
        Initialize the base login handler
        
        Args:
            driver: Selenium WebDriver instance
            credentials: Dict with login credentials (email, password, etc.)
        """
        self.browser = driver
        self.credentials = credentials
    
    def login(self):
        """
        Perform login - must be implemented by subclass
        
        Returns:
            True if login successful, False otherwise
        """
        raise NotImplementedError("Subclass must implement login()")
    
    def is_logged_in(self):
        """
        Check if already logged in - can be overridden by subclass
        
        Returns:
            True if logged in, False otherwise
        """
        return False
