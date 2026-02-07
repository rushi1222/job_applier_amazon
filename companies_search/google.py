"""
GOOGLE JOB SCRAPER FLOW:

1. Initialize scraper with Google settings (__init__)
   - Sets up driver, positions, locations from config.yml
   - Initializes blacklists and contact info
   - Prepares scraper to search for jobs

2. Search jobs for all position/location combinations (search_jobs)
   - Loops through all position/location combinations
   - Calls _extract_jobs_from_page() for each search
   - Filters duplicates and saves new jobs to datastore
   - Returns list of new jobs found

3. Build Google search URLs (_build_google_search_url)
   - Creates direct Google jobs search URL with position & location parameters
   - Navigates to the Google jobs page
   - Waits 3 seconds for page to load

4. Extract jobs from page HTML (_extract_jobs_from_page) - MAIN PARSING LOGIC
   - Counts ul elements on page (51 found)
   - Pauses for debugging when ul is found
   - Finds li elements within ul containers
   - Extracts job data from each li element:
     * Job title from h3.QJPWVe
     * Job URL from a.WpHeLc link
     * Job location from span.r0wTof
   - Limits processing to 20 job-like elements to prevent timeout
   - Returns list of job dictionaries

5. Extract job IDs from URLs (_extract_job_id_from_url)
   - Parses Google job URLs to extract numeric job IDs
   - Uses regex to match job ID patterns
   - Returns job ID or "N/A" if extraction fails

6. Filter and save jobs
   - _filter_new_jobs: Removes duplicates using existing datastore
   - _save_jobs_to_datastore: Persists new jobs to googledatastore.txt
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
        
        # Check if we're in CI environment
        ci_environment = os.environ.get('GITHUB_ACTIONS') == 'true' or os.environ.get('CI') == 'true'
        if ci_environment:
            print("🤖 Running in CI environment - using enhanced anti-detection")
        
        # Iterate through each combination of position and location
        for position, location in searches:
            print(f"\nSearching for position: '{position}' in location: '{location}'")
            
            # Try multiple approaches if blocked
            success = False
            approaches = ['direct_url']  # Can add more approaches later
            
            for approach in approaches:
                try:
                    if approach == 'direct_url':
                        # Build direct URL and navigate to Google search results
                        search_url = self._build_google_search_url(position, location)
                        print(f"Navigated to: {search_url}")
                        
                        # Extract jobs from results page
                        page_jobs = self._extract_jobs_from_page()
                        
                        # Check if we got results or if we were blocked
                        if len(page_jobs) > 0:
                            self.all_scraped_jobs.extend(page_jobs)
                            success = True
                            break
                        elif ci_environment:
                            print("⚠️  No jobs found - possible blocking in CI environment")
                        else:
                            print("ℹ️  No new jobs for this search combination")
                            success = True  # Not blocked, just no results
                            break
                            
                except Exception as e:
                    print(f"❌ Approach '{approach}' failed: {e}")
                    continue
            
            if not success and ci_environment:
                print("🚫 All approaches failed - Google may be blocking CI access")
        
        # After all searches, check for duplicates and save
        new_jobs = self._filter_new_jobs()
        if new_jobs:
            self._save_jobs_to_datastore(new_jobs)
        else:
            if len(self.all_scraped_jobs) == 0 and ci_environment:
                print(f"\n⚠️  {self.company_name.upper()}: No jobs scraped - likely blocked by anti-bot protection")
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
        
        # Add anti-detection measures for CI environments
        ci_environment = os.environ.get('GITHUB_ACTIONS') == 'true' or os.environ.get('CI') == 'true'
        if ci_environment:
            print("🤖 CI environment detected - applying anti-detection measures")
            try:
                # Set realistic user agent if not already set
                self.browser.execute_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                        configurable: true
                    });
                """)
            except Exception as e:
                print(f"⚠️  Failed to apply webdriver detection removal: {e}")
            # Add slight delays to mimic human behavior
            time.sleep(2)
        
        print(f"Direct Google search URL: {search_url}")
        self.browser.get(search_url)
        time.sleep(7 if ci_environment else 5)  # Longer wait in CI
        
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
            # space_continue(self.browser, "Google search submission failed - check buttons")
    
    # 4. HTML PARSER: Extract job data from Google's page HTML
    def _extract_jobs_from_page(self):
        """Extract job titles, URLs, and IDs from the current page. Returns list of job dicts."""
        jobs = []
        
        try:
            # Check if we're blocked or on an error page
            page_title = self.browser.title.lower()
            if 'blocked' in page_title or 'error' in page_title or 'access denied' in page_title:
                print("⚠️  Possible bot detection - page title suggests blocking")
                print(f"Page title: {self.browser.title}")
                return []
            
            # Wait for page to load and trigger lazy loading
            print("Waiting for page to load...")
            ci_environment = os.environ.get('GITHUB_ACTIONS') == 'true' or os.environ.get('CI') == 'true'
            initial_wait = 8 if ci_environment else 5
            time.sleep(initial_wait)
            
            # Scroll to trigger lazy loading (with human-like behavior)
            self.browser.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)
            self.browser.execute_script("window.scrollTo(0, 1000);")
            time.sleep(2)
            self.browser.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Find all <a> tags with href containing "jobs/results/"
            print("\n🔍 Searching for job links...")
            all_links = self.browser.find_elements(By.TAG_NAME, 'a')
            job_links = []
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    if href and 'jobs/results/' in href:
                        job_links.append({
                            'element': link,
                            'href': href,
                            'text': link.text.strip()
                        })
                except:
                    pass
            
            # Check if we found any job links
            if not job_links:
                print("❌ No job links found - checking page content")
                page_source = self.browser.page_source[:1000]  # First 1000 chars
                print(f"Page source preview: {page_source}")
                
                # Check for common blocking indicators
                blocking_indicators = ['captcha', 'verify', 'robot', 'automated', 'blocked']
                if any(indicator in page_source.lower() for indicator in blocking_indicators):
                    print("🚫 Bot detection triggered - Google is blocking automated access")
                    return []
            
            print(f"Found {len(job_links)} <a> tags with 'jobs/results/' in href:")
            for i, job_link in enumerate(job_links[:10]):  # Show first 10
                print(f"  Link[{i}]: href='{job_link['href'][:100]}...' | text='{job_link['text'][:50]}...'")
            
            # Extract job data from URLs
            if job_links:
                print(f"\n✓ Processing {len(job_links)} job links...")
                
                extracted_jobs_count = 0
                for i, job_link_data in enumerate(job_links[:20]):  # Limit to first 20
                    try:
                        job_url = job_link_data['href']
                        
                        # Extract job ID from URL using existing function
                        job_id = self._extract_job_id_from_url(job_url)
                        
                        # Extract job title from URL slug
                        # URL format: jobs/results/123456-job-title-here
                        title = "Unknown"
                        if 'jobs/results/' in job_url:
                            # Get the part after job ID
                            import re
                            match = re.search(r'jobs/results/\d+-(.*?)(?:\?|$)', job_url)
                            if match:
                                # Convert URL slug to readable title
                                title_slug = match.group(1)
                                title = title_slug.replace('-', ' ').title()
                        
                        if job_id == "N/A" or not title or title == "Unknown":
                            print(f"  ⚠️  Skipped link {i+1} - invalid data (ID={job_id}, title={title})")
                            continue
                        
                        # Create job dictionary
                        job = {
                            'job_id': job_id,
                            'title': title,
                            'url': job_url,
                            'location': "N/A",  # Location not available in URL
                            'posted_date': None  # Date not available
                        }
                        
                        jobs.append(job)
                        extracted_jobs_count += 1
                        print(f"  ✓ [{extracted_jobs_count}] {title} | ID: {job_id}")
                        
                    except Exception as e:
                        print(f"  ❌ Error extracting job {i+1}: {e}")
                        continue
                        
                print(f"\n✅ Extracted {extracted_jobs_count} jobs from {len(job_links)} job links")
                
                # Save to data/google/googledatastore.txt
                if jobs:
                    self._save_to_google_txt(jobs)
            else:
                print("\n❌ No job links found on page")
                
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

    def _save_to_google_txt(self, jobs):
        """Save jobs to data/google/googledatastore.txt file in CSV format like Amazon."""
        try:
            # Create directory if it doesn't exist
            google_dir = os.path.join('data', 'google')
            os.makedirs(google_dir, exist_ok=True)
            
            google_txt_path = os.path.join(google_dir, 'googledatastore.txt')
            
            # Read existing job IDs to avoid duplicates
            existing_job_ids = set()
            if os.path.exists(google_txt_path):
                with open(google_txt_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            job_id = line.split(',')[0]
                            existing_job_ids.add(job_id)
            
            # Filter out jobs that already exist
            new_jobs = [job for job in jobs if job['job_id'] not in existing_job_ids]
            
            if not new_jobs:
                print(f"\n💾 No new jobs to save - all {len(jobs)} jobs already exist in googledatastore.txt")
                return
            
            # Append only new jobs to file in CSV format
            with open(google_txt_path, 'a', encoding='utf-8') as f:
                for job in new_jobs:
                    # Format: job_id,title,url,null,null (no location or date available)
                    line = f"{job['job_id']},{job['title']},{job['url']},null,null\n"
                    f.write(line)
            
            print(f"\n💾 Saved {len(new_jobs)} new jobs to {google_txt_path} (skipped {len(jobs) - len(new_jobs)} duplicates)")
            
        except Exception as e:
            print(f"❌ Error saving to googledatastore.txt: {e}")
            traceback.print_exc()
    
    def no_more_jobs(self):
        # Placeholder function to determine if there are more jobs to apply for
        return False
