"""
Continuous job scraper with 30-minute intervals
Run this script on any server (Railway, Render, Heroku, etc.)
"""

import schedule
import time
import subprocess
import sys
import os

def run_job_scraper():
    """Run the main job scraper"""
    print(f"🚀 Running job scraper at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        result = subprocess.run([sys.executable, 'main.py'], 
                              capture_output=True, 
                              text=True, 
                              timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            print("✅ Job scraper completed successfully")
            print("STDOUT:", result.stdout[-500:])  # Last 500 chars
        else:
            print("❌ Job scraper failed")
            print("STDERR:", result.stderr[-500:])
            
    except subprocess.TimeoutExpired:
        print("⏰ Job scraper timed out after 5 minutes")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")

def main():
    print("🕐 Starting continuous job scraper (every 30 minutes)")
    
    # Schedule the job every 30 minutes
    schedule.every(30).minutes.do(run_job_scraper)
    
    # Run immediately on startup
    run_job_scraper()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()