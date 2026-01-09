import time
import os
from datetime import datetime
from itertools import product
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback
from .base_scraper import BaseScraper


class AmazonJobApplier(BaseScraper):
    """Amazon job scraper - extends BaseScraper"""
    
    def __init__(self, parameters, driver):
        # Initialize base scraper
        super().__init__('amazon', parameters, driver)
        
        # Amazon-specific parameters
        self.email = parameters.get('email')
        self.password = parameters.get('password')
        self.amazon_url = parameters.get('amazon_url')
        
        self.seen_jobs = []  # Keep track of jobs you've already applied for
        self.title_blacklist = parameters.get('titleBlacklist', []) or []
        self.company_blacklist = parameters.get('companyBlacklist', []) or []
        self.contact_info = parameters.get('contact', {})
        self.experience = parameters.get('experience', {})
        self.submission = False  # Flag to track successful submission


   

    def search_jobs(self):
        """Search for jobs by positions and locations from config and scrape first page only."""
        print("Starting job search...")
        
        # Generate all combinations of positions and locations
        searches = list(product(self.positions, self.locations))
        print(f"Generated {len(searches)} search combinations")
        
        # Iterate through each combination of position and location
        for position, location in searches:
            print(f"\nSearching for position: '{position}' in location: '{location}'")
            
            position_query = position.replace(' ', '+')
            # Use location as-is (e.g., "USA") - keep original case, don't convert
            location_query = location.replace(' ', '+')

            # Build search URL matching Amazon's format with country parameter
            # Note: latitude/longitude are optional and may be auto-filled by Amazon
            search_url = f"https://www.amazon.jobs/en/search?base_query={position_query}&loc_query={location_query}&country={location_query}&invalid_location=false&city=&region=&county="
            
            print(f"Search URL: {search_url}")
            self.browser.get(search_url)
            time.sleep(3)
            
            # Click search button if it exists
            try:
                search_button = WebDriverWait(self.browser, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Search jobs']"))
                )
                search_button.click()
                time.sleep(3)  # Wait longer for results to load
            except:
                print("Search button not found or search already executed")
            
            # Sort by most recent
            self._sort_by_recent()
            
            # Extract jobs from first page only
            page_jobs = self._extract_jobs_from_page()
            self.all_scraped_jobs.extend(page_jobs)
        
        # After all searches, check for duplicates and save
        new_jobs = self._filter_new_jobs()
        if new_jobs:
            self._save_jobs_to_datastore(new_jobs)
        else:
            print(f"\n{self.company_name.upper()}: No new jobs found. All jobs already in datastore.")
        
        return new_jobs  # Return new jobs instead of sending email
    
    
    def _sort_by_recent(self):
        """Sort jobs by most recent posted date."""
        try:
            # Wait for page to fully load and results to appear
            time.sleep(3)
            
            # Try URL parameter first (if supported)
            current_url = self.browser.current_url
            if 'sort=' not in current_url:
                # Try adding sort parameter to URL
                sort_url = current_url + ('&' if '?' in current_url else '?') + 'sort=recent'
                try:
                    self.browser.get(sort_url)
                    time.sleep(2)
                    print("Sorted by most recent (via URL parameter)")
                    return
                except:
                    pass
            
            # Try to find sort dropdown using multiple strategies
            # Strategy 1: Look for select dropdown
            try:
                from selenium.webdriver.support.ui import Select
                sort_selects = self.browser.find_elements(By.TAG_NAME, 'select')
                for sort_select in sort_selects:
                    try:
                        select = Select(sort_select)
                        # Try to select "Most recent"
                        options = [opt.text.strip() for opt in select.options]
                        if any('most recent' in opt.lower() for opt in options):
                            select.select_by_visible_text([opt for opt in options if 'most recent' in opt.lower()][0])
                            print("Sorted by most recent (via select dropdown)")
                            time.sleep(2)
                            return
                    except:
                        continue
            except:
                pass
            
            # Strategy 2: Look for button/dropdown that shows "Sort by:"
            try:
                # Find button containing "Sort by"
                sort_buttons = self.browser.find_elements(By.XPATH, "//button[contains(., 'Sort by') or contains(@aria-label, 'Sort')]")
                if not sort_buttons:
                    sort_buttons = self.browser.find_elements(By.XPATH, "//div[contains(@class, 'sort')]//button | //*[contains(@class, 'sort')]//button")
                
                for sort_button in sort_buttons:
                    try:
                        sort_button.click()
                        time.sleep(1)
                        
                        # Look for "Most recent" option after clicking
                        recent_options = self.browser.find_elements(By.XPATH, 
                            "//a[contains(text(), 'Most recent')] | "
                            "//button[contains(text(), 'Most recent')] | "
                            "//li[contains(text(), 'Most recent')] | "
                            "//div[contains(text(), 'Most recent')] | "
                            "//span[contains(text(), 'Most recent')]"
                        )
                        
                        if recent_options:
                            recent_options[0].click()
                            print("Sorted by most recent (via button dropdown)")
                            time.sleep(2)
                            return
                    except:
                        continue
            except Exception as e:
                pass
            
            # Strategy 3: Try to find dropdown by looking for elements with "Most recent" text nearby
            try:
                # Scroll to top to find sort controls
                self.browser.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
                # Look for any clickable element near "Most recent" text
                all_elements = self.browser.find_elements(By.XPATH, "//*[contains(text(), 'Most recent')]")
                for element in all_elements:
                    try:
                        # Try to click parent element if it's clickable
                        parent = element.find_element(By.XPATH, "./..")
                        if parent.tag_name in ['button', 'a', 'li']:
                            parent.click()
                            print("Sorted by most recent (via element click)")
                            time.sleep(2)
                            return
                        else:
                            element.click()
                            print("Sorted by most recent (via direct click)")
                            time.sleep(2)
                            return
                    except:
                        continue
            except:
                pass
            
            print("Could not find sort dropdown - jobs may already be sorted by default")
            
        except Exception as e:
            print(f"Could not sort by recent: {e}. Continuing with default sort...")
    
    def _extract_jobs_from_page(self):
        """Extract job titles, URLs, and IDs from the current page. Returns list of job dicts."""
        jobs = []
        try:
            job_tiles = WebDriverWait(self.browser, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'job-tile'))
            )
            
            print(f"\nFound {len(job_tiles)} jobs on this page:\n")
            
            for job_tile in job_tiles:
                try:
                    job_title = job_tile.find_element(By.CLASS_NAME, 'job-title').text
                    job_link = job_tile.find_element(By.CLASS_NAME, 'job-link').get_attribute('href')
                    
                    # Extract job ID from URL (format: /jobs/JOB_ID/job-title)
                    job_id = self._extract_job_id_from_url(job_link)
                    
                    # Try to extract location
                    location = "N/A"
                    try:
                        location_elem = job_tile.find_element(By.CLASS_NAME, 'location-and-id')
                        location = location_elem.text.split('|')[0].strip() if '|' in location_elem.text else location_elem.text.strip()
                    except:
                        try:
                            # Alternative selector
                            location_elem = job_tile.find_element(By.CSS_SELECTOR, '.location')
                            location = location_elem.text.strip()
                        except:
                            pass
                    
                    # Try to extract posted date
                    posted_date = "N/A"
                    try:
                        date_elem = job_tile.find_element(By.CLASS_NAME, 'posting-date')
                        posted_date = date_elem.text.strip()
                    except:
                        try:
                            # Alternative selector - sometimes in data attributes
                            posted_date = job_tile.get_attribute('data-posted-date')
                            if not posted_date:
                                posted_date = "N/A"
                        except:
                            pass
                    
                    job_data = {
                        'job_id': job_id,
                        'title': job_title,
                        'url': job_link,
                        'location': location,
                        'posted_date': posted_date
                    }
                    
                    jobs.append(job_data)
                    print(f"Title: {job_title}")
                    print(f"URL: {job_link}")
                    print(f"Job ID: {job_id}")
                    print(f"Location: {location}")
                    print(f"Posted: {posted_date}\n")
                    
                except Exception as e:
                    print(f"Error extracting job details: {e}")
                    continue
        
        except Exception as e:
            print(f"Error extracting jobs from page: {e}")
            traceback.print_exc()
        
        return jobs
    
    def _extract_job_id_from_url(self, url):
        """Extract job ID from Amazon jobs URL."""
        try:
            # URL format: https://www.amazon.jobs/en/jobs/JOB_ID/job-title
            parts = url.split('/jobs/')
            if len(parts) > 1:
                job_id = parts[1].split('/')[0]
                return job_id
        except:
            pass
        return None


    
    def no_more_jobs(self):
        # Placeholder function to determine if there are more jobs to apply for
        return False
    
   

      
      




