import time
import os
import smtplib
from datetime import datetime
from itertools import product
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback

applied_jobs_file = 'applied_jobs.txt'
failed_jobs_file = 'failed_jobs.txt'
datastore_file = 'datastore.txt'
failed_jobs = []


class AmazonJobApplier:
    def __init__(self, parameters, driver):
        self.browser = driver
        self.email = parameters.get('email')
        self.password = parameters.get('password')
        self.amazon_url = parameters.get('amazon_url')
        
        self.positions = parameters.get('positions', [])
        self.locations = parameters.get('locations', [])
        self.seen_jobs = []  # Keep track of jobs you've already applied for
        self.title_blacklist = parameters.get('titleBlacklist', []) or []
        self.company_blacklist = []  # Add companies to this list if needed
        self.company_blacklist = parameters.get('companyBlacklist', []) or []
        self.contact_info = parameters.get('contact', {})
        self.experience = parameters.get('experience', {})
        self.submission = False  # Flag to track successful submission
        
        # Email configuration
        email_config = parameters.get('email_config', {})
        self.sender_email = email_config.get('sender_email', '')
        self.sender_password = email_config.get('sender_password', '')
        self.recipient_email = email_config.get('recipient_email', '')
        
        # Store all scraped jobs
        self.all_scraped_jobs = []


   

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
        
        # After all searches, check for duplicates and notify
        new_jobs = self._filter_new_jobs()
        if new_jobs:
            self._save_jobs_to_datastore(new_jobs)
            self._send_email_notification(new_jobs)
        else:
            print("\nNo new jobs found. All jobs already in datastore.")
    
    
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
                    
                    job_data = {
                        'job_id': job_id,
                        'title': job_title,
                        'url': job_link
                    }
                    
                    jobs.append(job_data)
                    print(f"Title: {job_title}")
                    print(f"URL: {job_link}")
                    print(f"Job ID: {job_id}\n")
                    
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


    def _filter_new_jobs(self):
        """Filter out jobs that already exist in datastore.txt. Returns list of new jobs."""
        existing_job_ids = self._load_datastore()
        new_jobs = []
        
        for job in self.all_scraped_jobs:
            job_id = job.get('job_id')
            if job_id and job_id not in existing_job_ids:
                new_jobs.append(job)
        
        print(f"\nTotal jobs scraped: {len(self.all_scraped_jobs)}")
        print(f"New jobs found: {len(new_jobs)}")
        print(f"Duplicate jobs (skipped): {len(self.all_scraped_jobs) - len(new_jobs)}")
        
        return new_jobs
    
    def _load_datastore(self):
        """Load existing job IDs from datastore.txt. Returns set of job IDs."""
        existing_ids = set()
        if os.path.exists(datastore_file):
            try:
                with open(datastore_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            # Handle both formats: just ID or ID,title,url,date
                            job_id = line.split(',')[0]
                            existing_ids.add(job_id)
            except Exception as e:
                print(f"Error loading datastore: {e}")
        return existing_ids
    
    def _save_jobs_to_datastore(self, jobs):
        """Save new jobs to datastore.txt."""
        try:
            with open(datastore_file, 'a', encoding='utf-8') as f:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for job in jobs:
                    # Format: job_id,title,url,date
                    line = f"{job['job_id']},{job['title']},{job['url']},{current_time}\n"
                    f.write(line)
            print(f"\nSaved {len(jobs)} new jobs to {datastore_file}")
        except Exception as e:
            print(f"Error saving to datastore: {e}")
    
    def _send_email_notification(self, jobs):
        """Send email notification with new jobs."""
        if not self.sender_email or not self.sender_password or not self.recipient_email:
            print("Email configuration missing. Skipping email notification.")
            return
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'New Amazon Jobs Found - {len(jobs)} positions'
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            
            # Create email body
            text_body = self._format_email_text(jobs)
            html_body = self._format_email_html(jobs)
            
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email via Gmail SMTP
            print(f"\nSending email to {self.recipient_email}...")
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            print("Email sent successfully!")
        
        except Exception as e:
            print(f"Error sending email: {e}")
            traceback.print_exc()
    
    def _format_email_text(self, jobs):
        """Format jobs as plain text for email."""
        text = f"Found {len(jobs)} new Amazon job(s):\n\n"
        for i, job in enumerate(jobs, 1):
            text += f"{i}. {job['title']}\n"
            text += f"   Job ID: {job['job_id']}\n"
            text += f"   Link: {job['url']}\n\n"
        return text
    
    def _format_email_html(self, jobs):
        """Format jobs as HTML for email."""
        html = f"""
        <html>
          <body>
            <h2>Found {len(jobs)} new Amazon job(s):</h2>
            <ul>
        """
        for job in jobs:
            html += f"""
              <li>
                <strong>{job['title']}</strong><br>
                Job ID: {job['job_id']}<br>
                <a href="{job['url']}">View Job</a>
              </li><br>
            """
        html += """
            </ul>
          </body>
        </html>
        """
        return html


    

    
    
    def no_more_jobs(self):
        # Placeholder function to determine if there are more jobs to apply for
        return False
    
   

      
      




