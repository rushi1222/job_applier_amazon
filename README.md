# job_applier_amazon

Plan to Automate Amazon Job Applications
Navigate to Job Listings Page: We'll first write code to navigate to the page that lists all the jobs for a given position and location (you’ve already handled the URL part). We’ll extract the job listings by targeting elements like:

Job title (<h3 class="job-title">)
Job ID (<div class="job" data-job-id="xxxxxx">)
Location and other details.
Extract Job IDs: Each job listing contains a unique data-job-id value. We'll log these IDs in a file (e.g., applied_jobs.txt). This way, we can easily track which jobs have already been applied to in past runs and skip them during subsequent automation runs.

Apply for Jobs: For each job ID that hasn’t been applied for yet:

Navigate to the individual job page by clicking the job link (<a class="job-link">).
Click the “Apply Now” button (<a id="apply-button">) to start the application process.
Handle Application Forms: After clicking "Apply Now," the form sections (like contact info, general questions, resume upload, etc.) will appear. We'll write code to:

Check if any form sections are pre-filled and skip them if so.
Identify unfilled sections (like job-specific questions, work eligibility, etc.) and fill them out automatically.
Submit the form once all sections are complete.
Log Completed Applications: After a successful application, we'll log the job ID in applied_jobs.txt to avoid reapplying to the same job in future runs.

Next Steps
We'll first write a script that fetches all job listings from the page, extracts their job IDs and URLs, and saves them.
Then, we will handle the navigation to individual job pages and click the "Apply Now" button.
Finally, we will handle form sections one by one and complete the application.
