"""
APPLE JOB SCRAPER FLOW:

Apple's search API turned out not to be usable as a per-position keyword
search (see notes below), so unlike google.py/amazon.py this scraper does
NOT search per configured position. Instead it pulls a broad "newest first"
sweep of Apple's entire jobs feed, keeps only USA-located software-titled
postings, and lets the shared datastore diff (BaseScraper) decide what's
actually new. New jobs found this way carry no 'position' tag and are sent
to every recipient (see utils/email_sender.py's handling of position-less
jobs).

1. Initialize scraper with Apple settings (__init__)
   - Sets up locations from config.yml
   - Creates a requests.Session() (no Selenium browser needed - Apple exposes
     the same internal JSON API its own website frontend uses)

2. Search for newest jobs (search_jobs)
   - Fetches a CSRF token once per run (_get_csrf_token)
   - Calls _fetch_newest_us_jobs() to sweep the newest-sorted feed
   - Filters duplicates and saves new jobs to datastore
   - Returns list of new jobs found

3. Fetch a CSRF token (_get_csrf_token)
   - GET https://jobs.apple.com/api/v1/CSRFToken
   - Token comes back in the X-Apple-CSRF-Token response header
   - Session cookies are stored automatically by requests.Session()

4. Sweep the newest-sorted feed (_fetch_newest_us_jobs) - MAIN FETCH LOGIC
   - POST https://jobs.apple.com/api/v1/search once per page, up to MAX_PAGES
   - Body: {"query": "", "page": N, "locale": "en-us", "sort": "newest",
            "filters": {}, "format": "json"}
   - An empty query with sort=newest returns Apple's entire jobs feed
     (~6000 open roles worldwide), newest-refreshed first. There is no
     working server-side location filter (verified: filters.location/
     postLocation/countryID are all silently ignored - totalRecords never
     changes), so USA filtering happens client-side after fetching.
   - The first several pages are dominated by bulk-refreshed international
     retail postings that share near-identical timestamps; genuine fresh US
     postings are mixed in further down, which is why this paginates deep
     (MAX_PAGES=15, ~300 raw jobs) instead of reading only page 1.
   - After the location filter, a title-keyword filter (_is_software_title)
     keeps only postings that look like software engineering roles. Apple's
     own team categorization isn't reliable for this (software/firmware
     roles show up under the Hardware team too, and non-engineering teams
     can contain software-titled roles), so this matches on title text
     directly instead.

5. Extract job data from the JSON response
   - Maps Apple's response fields (positionId, postingTitle, locations, postingDate)
     to the same job dict shape used by google.py/amazon.py, minus 'position'
   - Builds the public job URL from positionId + transformedPostingTitle

6. Filter and save jobs
   - _filter_new_jobs: Removes duplicates using existing datastore
   - _save_jobs_to_datastore: Persists new jobs to appledatastore.txt
"""

import traceback

import requests

from .base_scraper import BaseScraper

CSRF_URL = "https://jobs.apple.com/api/v1/CSRFToken"
SEARCH_URL = "https://jobs.apple.com/api/v1/search"
MAX_PAGES = 15


class AppleJobApplier(BaseScraper):
    """Apple job scraper - extends BaseScraper. Uses Apple's internal JSON API
    directly via requests instead of Selenium, since no browser rendering is
    needed to get structured job data."""

    # 1. SETUP: Initialize Apple scraper with config parameters
    def __init__(self, parameters, driver):
        # Initialize base scraper (driver is accepted for interface
        # consistency with main.py but unused - no browser needed)
        super().__init__('apple', parameters, driver)

        self.contact_info = parameters.get('contact', {})
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    # 2. MAIN SEARCH: Sweep the newest-sorted feed and filter to USA
    def search_jobs(self):
        """Fetch Apple's newest USA job postings and return the ones not yet seen."""
        print("Starting Apple job search...")

        csrf_token = self._get_csrf_token()
        if not csrf_token:
            print("❌ Could not obtain Apple CSRF token - aborting Apple search")
            return []

        for location in self.locations:
            print(f"\nSweeping newest Apple postings for location: '{location}'")
            self.all_scraped_jobs.extend(self._fetch_newest_us_jobs(location, csrf_token))

        # Deduplicate all_scraped_jobs by job_id (multiple locations may return same jobs)
        seen_ids = set()
        deduplicated_jobs = []
        for job in self.all_scraped_jobs:
            job_id = job.get('job_id')
            if job_id and job_id not in seen_ids:
                seen_ids.add(job_id)
                deduplicated_jobs.append(job)

        if len(self.all_scraped_jobs) != len(deduplicated_jobs):
            print(f"🔍 Removed {len(self.all_scraped_jobs) - len(deduplicated_jobs)} duplicate jobs across locations")

        self.all_scraped_jobs = deduplicated_jobs

        # After sweeping, check for duplicates against the datastore and save
        new_jobs = self._filter_new_jobs()
        if new_jobs:
            self._save_jobs_to_datastore(new_jobs)
        else:
            print(f"\n{self.company_name.upper()}: No new jobs found. All jobs already in datastore.")

        return new_jobs

    # 3. CSRF: Fetch the token Apple's search API requires
    def _get_csrf_token(self):
        """Fetch a CSRF token from Apple's careers site. Returns the token string or None."""
        try:
            response = self.session.get(
                CSRF_URL,
                headers={"Referer": "https://jobs.apple.com/en-us/search"},
                timeout=15,
            )
            token = response.headers.get("X-Apple-CSRF-Token")
            if not token:
                print(f"⚠️  No CSRF token in response (status {response.status_code})")
            return token
        except Exception as e:
            print(f"Error fetching Apple CSRF token: {e}")
            return None

    # 4. FETCH: Page through the newest-sorted feed, keeping only USA postings
    def _fetch_newest_us_jobs(self, location, csrf_token):
        """Sweep up to MAX_PAGES of Apple's newest-sorted feed. Returns list of job dicts."""
        jobs = []
        skipped_location = 0
        skipped_title = 0

        for page in range(1, MAX_PAGES + 1):
            body = {
                "query": "",
                "page": page,
                "locale": "en-us",
                "sort": "newest",
                "filters": {},
                "format": "json",
            }

            try:
                response = self.session.post(
                    SEARCH_URL,
                    json=body,
                    headers={
                        "X-Apple-CSRF-Token": csrf_token,
                        "Referer": "https://jobs.apple.com/en-us/search",
                    },
                    timeout=20,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"Error fetching Apple jobs page {page}: {e}")
                traceback.print_exc()
                break

            results = data.get("res", {}).get("searchResults", [])
            if not results:
                print(f"Page {page}: no more results, stopping early")
                break

            for result in results:
                job_locations = result.get('locations', [])
                if not self._matches_configured_location(job_locations, location):
                    skipped_location += 1
                    continue

                title = result.get('postingTitle')
                if not self._is_software_title(title):
                    skipped_title += 1
                    continue

                job_id = result.get('positionId')
                slug = result.get('transformedPostingTitle', '')
                job_url = f"https://jobs.apple.com/en-us/details/{job_id}/{slug}"
                posted_date = result.get('postingDate', 'N/A')
                location_str = ", ".join(
                    loc.get('name') or loc.get('countryName') or 'N/A'
                    for loc in job_locations
                ) if job_locations else "N/A"

                job_data = {
                    'job_id': job_id,
                    'title': title,
                    'url': job_url,
                    'location': location_str,
                    'posted_date': posted_date,
                    'position': None,  # not tied to a specific searched position
                }
                jobs.append(job_data)
                print(f"[page {page}] {title} | {location_str} | {posted_date}")

        print(f"\nSwept {MAX_PAGES} page(s): {len(jobs)} software job(s) kept, "
              f"{skipped_location} non-USA skipped, {skipped_title} non-software titles skipped")
        return jobs

    # 5. FILTER: Keep only jobs whose title indicates a software engineering role
    def _is_software_title(self, title):
        """Return True if the job title looks like a software engineering role.

        Apple's own team categorization (job['team']['teamCode']) isn't reliable
        for this - genuine software/firmware roles show up under the Hardware
        team too, and non-engineering teams (e.g. Operations and Supply Chain)
        can contain software-titled roles as well. Matching on the title
        directly catches software roles regardless of which team they're filed
        under; verified against a real 300-job sample with no false negatives
        against common alternate phrasings (backend/frontend/full stack/SDE/etc).
        """
        if not title:
            return False
        title_lower = title.lower()
        keywords = ['software', 'swe', 'developer', 'programmer']
        return any(keyword in title_lower for keyword in keywords)

    # 6. FILTER: Keep only jobs in the configured location (e.g. "USA")
    def _matches_configured_location(self, job_locations, location):
        """Return True if job_locations includes the configured location.

        Only USA is special-cased today since that's the only value in
        config.yml; other configured locations pass through unfiltered.
        """
        if not location or location.strip().lower() not in ('usa', 'united states', 'united states of america'):
            return True

        return any(
            loc.get('countryID') == 'iso-country-USA'
            or loc.get('countryName') == 'United States of America'
            for loc in job_locations
        )


if __name__ == '__main__':
    # Standalone test run: python -m companies_search.apple
    # (must be run as a module, not `python companies_search/apple.py`,
    # since this file uses a relative import for BaseScraper)
    import os
    import yaml

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base_dir, 'config.yml'), 'r') as f:
        config = yaml.safe_load(f)

    parameters = {
        'locations': config['job_search']['locations'],
        'contact': config.get('contact', {}),
    }

    scraper = AppleJobApplier(parameters, driver=None)
    found_jobs = scraper.search_jobs()

    print(f"\n=== RESULT: {len(found_jobs)} new job(s) ===")
    for found_job in found_jobs:
        print(f"{found_job['title']} | {found_job['location']} | {found_job['url']}")
