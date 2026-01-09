"""
Email notification sender
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import traceback


def send_failure_notification(company_name, error_message, email_config):
    """
    Send email notification when a company scraper fails
    
    Args:
        company_name: Name of the company that failed
        error_message: Error message/traceback
        email_config: Dict with sender_email, sender_password, recipient_email
    
    Returns:
        True if email sent successfully, False otherwise
    """
    sender_email = email_config.get('sender_email', '')
    sender_password = email_config.get('sender_password', '')
    recipient_email = email_config.get('recipient_email', [])
    
    # Ensure recipient_email is a list
    if isinstance(recipient_email, str):
        recipient_email = [recipient_email]
    
    if not sender_email or not sender_password or not recipient_email:
        print("Email configuration missing. Skipping failure notification.")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'❌ Job Scraper Failed - {company_name.upper()}'
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipient_email)
        
        # Create email body
        text_body = f"""
Job scraper FAILED for {company_name.upper()}

Error:
{error_message}

Please check and fix the code.

Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        html_body = f"""
<html>
  <body style="font-family: Arial, sans-serif;">
    <h3 style="color: #e74c3c;">❌ Job Scraper Failed - {company_name.upper()}</h3>
    <p><strong>Error:</strong></p>
    <pre style="background: #f4f4f4; padding: 10px; border-left: 3px solid #e74c3c;">{error_message}</pre>
    <p style="color: #7f8c8d;"><em>Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</em></p>
  </body>
</html>
"""
        
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        recipients_str = ', '.join(recipient_email)
        print(f"📧 Sending failure notification to {recipients_str}...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        
        print("✅ Failure notification sent!")
        return True
    
    except Exception as e:
        print(f"❌ Error sending failure notification: {e}")
        return False


def send_job_notification(jobs_by_company, email_config):
    """
    Send email notification with new jobs from multiple companies
    
    Args:
        jobs_by_company: Dict with company names as keys and list of jobs as values
                        Example: {'amazon': [job1, job2], 'google': [job3]}
        email_config: Dict with sender_email, sender_password, recipient_email
    
    Returns:
        True if email sent successfully, False otherwise
    """
    sender_email = email_config.get('sender_email', '')
    sender_password = email_config.get('sender_password', '')
    recipient_email = email_config.get('recipient_email', [])
    
    # Ensure recipient_email is a list
    if isinstance(recipient_email, str):
        recipient_email = [recipient_email]
    
    if not sender_email or not sender_password or not recipient_email:
        print("Email configuration missing. Skipping email notification.")
        return False
    
    # Count total jobs
    total_jobs = sum(len(jobs) for jobs in jobs_by_company.values())
    
    if total_jobs == 0:
        print("No new jobs to send in email.")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'New Job Postings Found - {total_jobs} positions across {len(jobs_by_company)} companies'
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipient_email)
        
        # Create email body
        text_body = _format_email_text(jobs_by_company, total_jobs)
        html_body = _format_email_html(jobs_by_company, total_jobs)
        
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email via Gmail SMTP
        recipients_str = ', '.join(recipient_email)
        print(f"\n📧 Sending email to {recipients_str}...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        
        print("✅ Email sent successfully!")
        return True
    
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        traceback.print_exc()
        return False


def _format_email_text(jobs_by_company, total_jobs):
    """Format jobs as plain text for email"""
    text = f"Found {total_jobs} new job(s):\n\n"
    
    for company_name, jobs in jobs_by_company.items():
        text += f"{company_name.upper()} ({len(jobs)} jobs):\n\n"
        
        for job in jobs:
            text += f"• {job['title']}\n"
            text += f"  {job['url']}\n"
            if job.get('job_id'):
                text += f"  🆔 Job ID: {job['job_id']}\n"
            if job.get('location') and job['location'] != 'N/A':
                text += f"  📍 {job['location']}\n"
            if job.get('posted_date') and job['posted_date'] != 'N/A':
                text += f"  📅 Posted: {job['posted_date']}\n"
            text += "\n"
    
    return text


def _format_email_html(jobs_by_company, total_jobs):
    """Format jobs as HTML for email"""
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h3>Found {total_jobs} new job(s)</h3>
    """
    
    for company_name, jobs in jobs_by_company.items():
        html += f"<h4>{company_name.upper()} ({len(jobs)} jobs)</h4><ul>"
        
        for job in jobs:
            html += f'<li><a href="{job["url"]}">{job["title"]}</a>'
            if job.get('job_id'):
                html += f'<br><span style="color: #666;">🆔 Job ID: {job["job_id"]}</span>'
            if job.get('location') and job['location'] != 'N/A':
                html += f'<br><span style="color: #666;">📍 {job["location"]}</span>'
            if job.get('posted_date') and job['posted_date'] != 'N/A':
                html += f'<br><span style="color: #666;">📅 {job["posted_date"]}</span>'
            html += '</li>'
        
        html += "</ul>"
    
    html += """
      </body>
    </html>
    """
    return html
