"""
Base scraper class for all company job scrapers
"""
import os
from datetime import datetime


class BaseScraper:
    """Base class for company-specific job scrapers"""
    
    def __init__(self, company_name, parameters, driver):
        """
        Initialize the base scraper
        
        Args:
            company_name: Name of the company (e.g., 'amazon', 'google')
            parameters: Dict with search parameters, credentials, etc.
            driver: Selenium WebDriver instance
        """
        self.company_name = company_name
        self.browser = driver
        self.parameters = parameters
        
        # Job search parameters
        self.positions = parameters.get('positions', [])
        self.locations = parameters.get('locations', [])
        
        # Data storage paths
        self.data_dir = os.path.join('data', company_name)
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.datastore_file = os.path.join(self.data_dir, f'{company_name}datastore.txt')
        self.failed_jobs_file = os.path.join(self.data_dir, 'failed_jobs.txt')
        self.download_dir = os.path.join(self.data_dir, 'downloaded_files')
        
        # Tracking
        self.all_scraped_jobs = []
        
    def search_jobs(self):
        """
        Main method to search for jobs - must be implemented by subclass
        
        Returns:
            List of new jobs found
        """
        raise NotImplementedError("Subclass must implement search_jobs()")
    
    def _load_datastore(self):
        """Load existing job IDs from datastore. Returns set of job IDs."""
        existing_ids = set()
        if os.path.exists(self.datastore_file):
            try:
                with open(self.datastore_file, 'r', encoding='utf-8') as f:
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
        """Save new jobs to datastore."""
        try:
            with open(self.datastore_file, 'a', encoding='utf-8') as f:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for job in jobs:
                    # Format: job_id,title,url,location,posted_date,scraped_timestamp
                    location = job.get('location', 'N/A')
                    posted_date = job.get('posted_date', 'N/A')
                    line = f"{job['job_id']},{job['title']},{job['url']},{location},{posted_date},{current_time}\n"
                    f.write(line)
            print(f"✅ Saved {len(jobs)} new jobs to {self.datastore_file}")
        except Exception as e:
            print(f"❌ Error saving to datastore: {e}")
    
    def _filter_new_jobs(self):
        """Filter out jobs that already exist in datastore. Returns list of new jobs."""
        existing_job_ids = self._load_datastore()
        new_jobs = []
        
        for job in self.all_scraped_jobs:
            job_id = job.get('job_id')
            if job_id and job_id not in existing_job_ids:
                new_jobs.append(job)
        
        print(f"\n📊 {self.company_name.upper()} - Total scraped: {len(self.all_scraped_jobs)} | "
              f"New: {len(new_jobs)} | Duplicates: {len(self.all_scraped_jobs) - len(new_jobs)}")
        
        return new_jobs
    
    def get_company_name(self):
        """Returns the company name"""
        return self.company_name
