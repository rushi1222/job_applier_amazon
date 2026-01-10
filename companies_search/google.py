"""
GOOGLE JOB SCRAPER FLOW:
1. Initialize scraper with Google settings (__init__)
   INPUT: parameters from config.yml, browser driver from main.py
   OUTPUT: None (initialization only)
   
2. Search jobs for all position/location combinations (search_jobs)
   INPUT: Called by main.py, uses self.positions & self.locations from config
   OUTPUT: List of new job dictionaries (sent to main.py for email)
   
3. Build Google search URLs with direct parameters (_build_google_search_url)
   INPUT: position & location strings from search_jobs loop
   OUTPUT: Direct navigation to Google search results page
   
4. Extract jobs from page HTML (_extract_jobs_from_page)
   INPUT: Current browser page HTML after URL navigation
   OUTPUT: List of job dictionaries with job_id, title, url, location, posted_date
   
5. Get job IDs from URLs (_extract_job_id_from_url)
   INPUT: job URLs extracted from HTML in step 4
   OUTPUT: Job ID string or None if extraction fails
   
6. Filter duplicates and save new jobs (_filter_new_jobs, _save_jobs_to_datastore)
   INPUT: all_scraped_jobs list and existing googledatastore.txt file
   OUTPUT: _filter_new_jobs returns new jobs list, _save_jobs_to_datastore saves to file
"""

import time
import os
from datetime import datetime
from itertools import product
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import traceback
from .base_scraper import BaseScraper
from utils.helpers import space_continue


class GoogleJobApplier(BaseScraper):
    """Google job scraper - extends BaseScraper"""
    
    # 1. SETUP: Initialize Google scraper with config parameters
    def __init__(self, parameters, driver):
        # Initialize base scraper
        super().__init__('google', parameters, driver)
        
        # Google-specific parameters (if needed later)
        self.seen_jobs = []  # Keep track of jobs you've already applied for
        self.title_blacklist = parameters.get('titleBlacklist', []) or []
        self.company_blacklist = parameters.get('companyBlacklist', []) or []
        self.contact_info = parameters.get('contact', {})
        self.experience = parameters.get('experience', {})
        self.submission = False  # Flag to track successful submission

    # 2. MAIN SEARCH: Loop through positions/locations and extract jobs
    def search_jobs(self):
        """Search for jobs by positions and locations from config and scrape first page only."""
        print("Starting Google job search...")
        
        # Generate all combinations of positions and locations
        searches = list(product(self.positions, self.locations))
        print(f"Generated {len(searches)} search combinations")
        
        # Iterate through each combination of position and location
        for position, location in searches:
            print(f"\nSearching for position: '{position}' in location: '{location}'")
            
            # Build direct URL and navigate to Google search results
            search_url = self._build_google_search_url(position, location)
            print(f"Navigated to: {search_url}")
            
            # Extract jobs from results page
            page_jobs = self._extract_jobs_from_page()
            self.all_scraped_jobs.extend(page_jobs)
        
        # After all searches, check for duplicates and save
        new_jobs = self._filter_new_jobs()
        if new_jobs:
            self._save_jobs_to_datastore(new_jobs)
        else:
            print(f"\n{self.company_name.upper()}: No new jobs found. All jobs already in datastore.")
        
        return new_jobs  # Return new jobs instead of sending email
    
    # 3. URL BUILDER: Create Google search URL with position and location
    def _build_google_search_url(self, position, location):
        """Build Google-specific search URL with direct parameters"""
        base_url = "https://www.google.com/about/careers/applications/jobs/results"
        
        # URL encode position and location for URL parameters
        from urllib.parse import quote
        position_encoded = quote(position)
        location_encoded = quote(location)
        
        # Build direct search URL with parameters
        search_url = f"{base_url}?q={position_encoded}&location={location_encoded}&sort_by=date"
        
        print(f"Direct Google search URL: {search_url}")
        self.browser.get(search_url)
        time.sleep(3)  # Wait for page to load
        
        return search_url
    
    def _submit_google_search(self):
        """Submit Google search form after filling fields"""
        try:
            # Look for common submit button patterns
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']", 
                "button[aria-label*='Search']",
                "button[aria-label*='Find']",
                ".search-button",
                "[data-testid*='search']"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = self.browser.find_element(By.CSS_SELECTOR, selector)
                    if submit_button.is_enabled():
                        print(f"Clicking submit button: {selector}")
                        submit_button.click()
                        time.sleep(3)
                        return
                except:
                    continue
            
            # If no submit button found, try pressing Enter on location field
            print("No submit button found, pressing Enter on location field")
            location_input = self.browser.find_element(By.ID, "c81")
            from selenium.webdriver.common.keys import Keys
            location_input.send_keys(Keys.RETURN)
            time.sleep(3)
            
        except Exception as e:
            print(f"Error submitting Google search: {e}")
            print("🛑 Pausing for debugging - check submit button")
            space_continue(self.browser, "Google search submission failed - check buttons")
    
    # 4. HTML PARSER: Extract job data from Google's page HTML
    def _extract_jobs_from_page(self):
        """Extract job titles, URLs, and IDs from the current page. Returns list of job dicts."""
        jobs = []
        
        try:
            # Find h2 with "Jobs search results" text, then navigate to ul child with li elements
            h2_elements = self.browser.find_elements(By.TAG_NAME, 'h2')
            jobs_section = None
            
            # Look for h2 containing "Jobs search results" or similar text
            for h2 in h2_elements:
                if 'job' in h2.text.lower() and ('result' in h2.text.lower() or 'search' in h2.text.lower()):
                    jobs_section = h2
                    print(f"Found jobs section: {h2.text}")
                    break
            
            if not jobs_section:
                print("No jobs section found, looking for ul with li children directly")
                # Fallback: look for ul elements with multiple li children
                ul_elements = self.browser.find_elements(By.TAG_NAME, 'ul')
                print(f"Total ul elements found on page: {len(ul_elements)}")
                
                for i, ul in enumerate(ul_elements):
                    li_elements = ul.find_elements(By.TAG_NAME, 'li')
                    if len(li_elements) > 3:  # Likely a job list if it has multiple items
                        print(f"ul[{i}] has {len(li_elements)} li elements - potential job container")
                        jobs_section = ul
                        
                # Use the ul with the most li elements (most likely job container)
                max_li_count = 0
                best_ul = None
                for ul in ul_elements:
                    li_count = len(ul.find_elements(By.TAG_NAME, 'li'))
                    if li_count > max_li_count:
                        max_li_count = li_count
                        best_ul = ul
                        
                if best_ul:
                    jobs_section = best_ul
                    print(f"Selected ul with {max_li_count} li elements as main job container")
            
            if jobs_section:
                # Find ul child under the jobs section
                if jobs_section.tag_name == 'h2':
                    # Navigate from h2 to find ul (could be sibling or in parent container)
                    parent = jobs_section.find_element(By.XPATH, './..')
                    ul_elements = parent.find_elements(By.TAG_NAME, 'ul')
                    if ul_elements:
                        ul_container = ul_elements[0]
                    else:
                        print("No ul found near h2, searching page-wide")
                        ul_container = self.browser
                else:
                    ul_container = jobs_section
                
                # Find all li elements in the ul container
                if ul_container.tag_name == 'ul':
                    li_elements = ul_container.find_elements(By.TAG_NAME, 'li')
                else:
                    li_elements = ul_container.find_elements(By.TAG_NAME, 'li')
                
                print(f"Found {len(li_elements)} job listing elements")
                
                # Add debugging: check if all li elements have job-like content
                job_like_lis = 0
                for li in li_elements:
                    try:
                        # Check if li has job-related div structure
                        main_divs = li.find_elements(By.XPATH, "./div[@jscontroller]")
                        if main_divs:
                            job_like_lis += 1
                    except:
                        pass
                        
                print(f"Of {len(li_elements)} li elements, {job_like_lis} appear to have job-like structure")
                
                # Only process job-like li elements to avoid browser timeout
                job_like_elements = []
                for li in li_elements:
                    try:
                        # Check if li has job-related div structure
                        main_divs = li.find_elements(By.XPATH, "./div[@jscontroller]")
                        if main_divs:
                            job_like_elements.append(li)
                            if len(job_like_elements) >= 20:  # Limit to first 20 job-like elements
                                break
                    except:
                        pass
                
                print(f"Processing {len(job_like_elements)} job-like li elements (limited to prevent timeout)")
                
                extracted_jobs_count = 0
                for i, li in enumerate(job_like_elements):
                    try:
                        print(f"Processing job-like element {i+1}/{len(job_like_elements)}")
                        
                        # Navigate hierarchy: li -> div[jscontroller] -> nested structure
                        main_div = li.find_element(By.XPATH, "./div[@jscontroller]")
                        
                        # Extract job title from deeply nested h3 (li > div > ... > h3.QJPWVe)
                        try:
                            title_element = main_div.find_element(By.CSS_SELECTOR, "h3.QJPWVe")
                            title = title_element.text.strip() if title_element else "N/A"
                        except:
                            title = "N/A"
                            print("No title found using CSS selector h3.QJPWVe, using default")
                            
                        if title == "N/A":
                            print(f"Skipped li element {i+1} - no title found")
                            continue  # Skip if no title found
                        
                        # Extract job URL from a.WpHeLc link (nested deep in structure)
                        job_url = "N/A"
                        try:
                            link_element = main_div.find_element(By.CSS_SELECTOR, "a.WpHeLc")
                            relative_url = link_element.get_attribute('href')
                            
                            if relative_url:
                                # Convert to full URL if relative
                                if relative_url.startswith('jobs/results'):
                                    job_url = f"https://www.google.com/about/careers/applications/{relative_url}"
                                elif relative_url.startswith('/'):
                                    job_url = f"https://www.google.com/about/careers/applications{relative_url}"
                                else:
                                    job_url = relative_url
                        except:
                            print(f"No valid job URL found for: {title}, using default")
                            
                        # Extract job ID from URL
                        job_id = self._extract_job_id_from_url(job_url)
                        
                        if not job_id or job_id == "N/A":
                            print(f"Could not extract job ID from URL: {job_url}, using default")
                            job_id = "N/A"
                        
                        # Extract location from span.r0wTof (li > div > ... > span.r0wTof)
                        location = "N/A"
                        try:
                            # Look for location spans in the structure
                            location_spans = main_div.find_elements(By.CSS_SELECTOR, "span.r0wTof")
                            if location_spans:
                                # Take first location span and clean it up
                                location_text = location_spans[0].text.strip()
                                if location_text:
                                    location = location_text
                        except:
                            print(f"No location found for job: {title}, using default")
                        
                        # Create job dictionary
                        job = {
                            'job_id': job_id,  # Keep N/A for debugging when extraction fails
                            'title': title,
                            'url': job_url,
                            'location': location,
                            'posted_date': "N/A"  # Google doesn't clearly show posted date, use default
                        }
                        
                        jobs.append(job)
                        extracted_jobs_count += 1
                        print(f"✓ Extracted job {extracted_jobs_count}: {title[:50]}... | {location}")
                        
                    except Exception as e:
                        print(f"Error extracting individual job {i+1}: {e}")
                        continue
                        
                print(f"\nSummary: Extracted {extracted_jobs_count} jobs out of {len(job_like_elements)} job-like li elements")
            else:
                print("No jobs section or ul container found")
                
        except Exception as e:
            print(f"Error extracting jobs from Google page: {e}")
            traceback.print_exc()
        
        return jobs
    
    # 5. ID EXTRACTOR: Get job ID from Google job URLs  
    def _extract_job_id_from_url(self, url):
        """Extract job ID from Google jobs URL."""
        try:
            # Skip if URL is default value
            if url == "N/A":
                return "N/A"
                
            # Google URL format: jobs/results/133098736233390790-job-title-slug
            # Extract the number part before the first hyphen
            import re
            
            # Pattern to match job ID in Google URLs
            match = re.search(r'jobs/results/(\d+)-', url)
            if match:
                return match.group(1)
            
            # Alternative pattern for different URL formats
            match = re.search(r'/(\d{10,})[-/]', url)
            if match:
                return match.group(1)
                
            print(f"Could not extract job ID from URL: {url}")
            return "N/A"  # Default for failed extraction
            
        except Exception as e:
            print(f"Error extracting job ID from URL {url}: {e}")
            return "N/A"  # Default for errors

    def no_more_jobs(self):
        # Placeholder function to determine if there are more jobs to apply for
        return False
