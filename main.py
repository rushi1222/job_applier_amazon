import yaml
import os
import importlib
import traceback
from dotenv import load_dotenv
from utils import init_browser, space_continue, send_job_notification, send_failure_notification


if __name__ == '__main__':
    print("="*70)
    print("🚀 Multi-Company Job Scraper")
    print("="*70)
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Load global configuration
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.yml')
    companies_path = os.path.join(base_dir, 'companies.yaml')
    
    print(f"\n📄 Loading configuration from {config_path}...")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    print(f"📄 Loading companies from {companies_path}...")
    with open(companies_path, "r") as f:
        companies_config = yaml.safe_load(f)
    
    # Extract global parameters with env var override for email credentials
    email_config = config.get('email', {})
    
    # Override with environment variables if present
    sender_email = os.getenv('GMAIL_SENDER_EMAIL', email_config.get('sender_email', ''))
    sender_password = os.getenv('GMAIL_SENDER_PASSWORD', email_config.get('sender_password', ''))
    recipient_email = os.getenv('RECIPIENT_EMAIL', '')
    
    # Parse recipient emails (comma-separated in env var, or list from config)
    if recipient_email:
        recipient_email_list = [email.strip() for email in recipient_email.split(',')]
    else:
        recipient_email_list = email_config.get('recipient_email', [])
    
    parameters = {
        'positions': config['job_search']['positions'],
        'locations': config['job_search']['locations'],
        'contact': config.get('contact', {}),
        'experience': config.get('experience', {}),
        'email_config': {
            'sender_email': sender_email,
            'sender_password': sender_password,
            'recipient_email': recipient_email_list
        },
    }
    
    # Initialize browser once for all companies
    download_dir = os.path.join(base_dir, "data", "downloads")
    browser = init_browser(headless=False, download_dir=download_dir)
    
    # Store all new jobs by company
    all_new_jobs = {}
    
    try:
        # Process each enabled company
        for company in companies_config.get('companies', []):
            if not company.get('enabled', False):
                print(f"\n⏭️  Skipping {company['name']} (disabled)")
                continue
            
            company_name = company['name']
            print(f"\n{'='*70}")
            print(f"🏢 Processing: {company_name.upper()}")
            print(f"{'='*70}")
            
            try:
                # Handle login if required
                if company.get('requires_login', False):
                    login_module_path = company.get('login_module')
                    if login_module_path:
                        print(f"🔐 Login required for {company_name}")
                        module_parts = login_module_path.rsplit('.', 1)
                        login_module = importlib.import_module(module_parts[0])
                        LoginClass = getattr(login_module, module_parts[1].replace('_login', '_login').title().replace('_', '') + 'Login' if '.' not in module_parts[1] else 'AmazonLogin')
                        
                        # For now, just skip login requirement
                        print(f"⚠️  Login handler exists but skipping for scraping")
                
                # Load and execute scraper
                search_module_path = company.get('search_module')
                if not search_module_path:
                    print(f"❌ No search module specified for {company_name}")
                    continue
                
                # Import the scraper class
                module_parts = search_module_path.rsplit('.', 1)
                scraper_module = importlib.import_module(search_module_path)
                
                # Get the scraper class - try multiple naming conventions
                possible_class_names = [
                    f"{company_name.capitalize()}JobApplier",  # AmazonJobApplier
                    f"{company_name.upper()}JobApplier",        # AMAZONJobApplier
                    f"{company_name.title().replace('_', '')}JobApplier",  # For multi-word companies
                ]
                
                ScraperClass = None
                for class_name in possible_class_names:
                    ScraperClass = getattr(scraper_module, class_name, None)
                    if ScraperClass:
                        print(f"✓ Found scraper class: {class_name}")
                        break
                
                if not ScraperClass:
                    print(f"❌ Could not find scraper class for {company_name}")
                    print(f"   Tried: {', '.join(possible_class_names)}")
                    print(f"   Available in module: {dir(scraper_module)}")
                    continue
                
                # Add company-specific config to parameters
                company_params = {**parameters}
                if 'credentials' in config:
                    company_params.update({
                        'email': config['credentials'].get('email'),
                        'password': config['credentials'].get('password'),
                        'amazon_url': config['credentials'].get('amazon_url'),  # Will be generic later
                    })
                
                # Create scraper instance and run
                scraper = ScraperClass(company_params, browser)
                new_jobs = scraper.search_jobs()
                
                if new_jobs:
                    all_new_jobs[company_name] = new_jobs
                    print(f"✅ {company_name.upper()}: Found {len(new_jobs)} new jobs")
                else:
                    print(f"ℹ️  {company_name.upper()}: No new jobs found")
                
            except Exception as e:
                error_msg = f"❌ Error processing {company_name}: {e}"
                print(error_msg)
                
                # Get full traceback
                error_traceback = traceback.format_exc()
                print(error_traceback)
                
                # Send failure notification email
                send_failure_notification(company_name, error_traceback, parameters['email_config'])
                continue
        
        # Send consolidated email if any new jobs found
        if all_new_jobs:
            total_jobs = sum(len(jobs) for jobs in all_new_jobs.values())
            print(f"\n{'='*70}")
            print(f"📧 Sending notification for {total_jobs} new jobs across {len(all_new_jobs)} companies")
            print(f"{'='*70}")
            send_job_notification(all_new_jobs, parameters['email_config'])
        else:
            print(f"\n{'='*70}")
            print("ℹ️  No new jobs found across any companies")
            print(f"{'='*70}")
    
    finally:
        print("\n🧹 Cleaning up...")
        browser.quit()
        print("✅ Browser closed successfully.")
        print("="*70)
