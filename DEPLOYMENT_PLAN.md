# Deployment Plan - Cloud Run Job Scheduler

## Project: Multi-Company Job Scraper
**Goal:** Deploy to Google Cloud Run Jobs with Cloud Scheduler (9am-7pm CT, every 30 min)

---

## Phase 1: Prepare for Containerization ✅

### 1.1 Create Dockerfile
- [ ] Create Dockerfile with Python 3.10+ base image
- [ ] Install Chrome and ChromeDriver for Selenium
- [ ] Copy application code
- [ ] Install Python dependencies from requirements.txt
- [ ] Set working directory and entry point

### 1.2 Update main.py for Cloud Run
- [ ] Remove `input()` prompt (blocks in cloud)
- [ ] Add proper exit handling
- [ ] Ensure all paths work in container environment

### 1.3 Create .dockerignore
- [ ] Exclude unnecessary files (venv, .git, __pycache__, etc.)
- [ ] Keep only essential code and config

### 1.4 Update requirements.txt
- [ ] Ensure all dependencies listed
- [ ] Pin versions for reproducibility

---

## Phase 2: Environment Variables & Secrets

### 2.1 Move Credentials to Environment Variables
- [ ] Remove hardcoded credentials from config.yml
- [ ] Update code to read from environment variables
- [ ] Create .env.example template

### 2.2 Set up Google Cloud Secret Manager
- [ ] Create secrets for:
  - Gmail sender email
  - Gmail sender password (app password)
  - Recipient emails
  - Any other sensitive data

### 2.3 Update code to use secrets
- [ ] Modify config loading to fetch from env vars
- [ ] Add fallback to config.yml for local development

---

## Phase 3: Build & Test Docker Image Locally

### 3.1 Build Docker Image
```bash
docker build -t job-scraper:latest .
```

### 3.2 Test Locally
```bash
docker run --env-file .env job-scraper:latest
```

### 3.3 Verify
- [ ] Scraper runs successfully
- [ ] Jobs are found and saved
- [ ] Email notifications work
- [ ] No errors in logs

---

## Phase 4: Google Cloud Setup

### 4.1 Create/Select GCP Project
- [ ] Create new project or select existing
- [ ] Enable billing (if not already)
- [ ] Note project ID

### 4.2 Enable Required APIs
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### 4.3 Create Artifact Registry Repository
```bash
gcloud artifacts repositories create job-scraper-repo \
  --repository-format=docker \
  --location=us-central1
```

---

## Phase 5: Deploy to Cloud Run

### 5.1 Build & Push Docker Image to Artifact Registry
```bash
# Tag image
docker tag job-scraper:latest \
  us-central1-docker.pkg.dev/PROJECT_ID/job-scraper-repo/job-scraper:latest

# Push to registry
docker push us-central1-docker.pkg.dev/PROJECT_ID/job-scraper-repo/job-scraper:latest
```

### 5.2 Create Cloud Run Job
```bash
gcloud run jobs create job-scraper \
  --image us-central1-docker.pkg.dev/PROJECT_ID/job-scraper-repo/job-scraper:latest \
  --max-retries 2 \
  --task-timeout 10m \
  --memory 2Gi \
  --cpu 1 \
  --region us-central1 \
  --set-secrets=GMAIL_SENDER_EMAIL=gmail-sender:latest,\
GMAIL_SENDER_PASSWORD=gmail-password:latest,\
RECIPIENT_EMAIL=recipient-email:latest
```

### 5.3 Test Manual Execution
```bash
gcloud run jobs execute job-scraper --region us-central1
```

### 5.4 Check Logs
```bash
gcloud logging read "resource.type=cloud_run_job" --limit 50
```

---

## Phase 6: Set Up Cloud Scheduler

### 6.1 Create Scheduler Job (Every 30 min, 9am-7pm CT)
```bash
gcloud scheduler jobs create http job-scraper-schedule \
  --location us-central1 \
  --schedule "*/30 9-19 * * *" \
  --time-zone "America/Chicago" \
  --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/PROJECT_ID/jobs/job-scraper:run" \
  --http-method POST \
  --oauth-service-account-email PROJECT_NUMBER-compute@developer.gserviceaccount.com
```

### 6.2 Test Scheduler
```bash
gcloud scheduler jobs run job-scraper-schedule --location us-central1
```

### 6.3 Verify Schedule
- [ ] Check logs at scheduled times
- [ ] Verify emails are received
- [ ] Monitor for failures

---

## Phase 7: Monitoring & Maintenance

### 7.1 Set Up Alerts
- [ ] Cloud Monitoring alert for job failures
- [ ] Budget alerts if cost exceeds threshold
- [ ] Email alert for scraper errors

### 7.2 Create Dashboard
- [ ] Job execution success rate
- [ ] Execution duration trends
- [ ] Cost tracking

### 7.3 Regular Maintenance
- [ ] Weekly log review
- [ ] Monthly cost review
- [ ] Update dependencies as needed

---

## Phase 8: Optimization (Optional)

### 8.1 Performance
- [ ] Reduce Docker image size
- [ ] Optimize Chrome flags for faster execution
- [ ] Parallel scraping for multiple companies

### 8.2 Cost Optimization
- [ ] Reduce CPU/memory if possible
- [ ] Adjust timeout to minimum needed
- [ ] Use cheaper regions if applicable

### 8.3 Features
- [ ] Add more companies
- [ ] Implement login functionality
- [ ] Add data analytics/reporting

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | 1-2 hours | None |
| Phase 2 | 1 hour | Phase 1 |
| Phase 3 | 30 min | Phase 1, 2 |
| Phase 4 | 30 min | GCP account |
| Phase 5 | 1 hour | Phase 3, 4 |
| Phase 6 | 30 min | Phase 5 |
| Phase 7 | 1 hour | Phase 6 |
| **Total** | **5-6 hours** | |

---

## Cost Estimate

- **Cloud Run Jobs:** $0-2/month (within free tier)
- **Cloud Scheduler:** $0/month (3 free jobs)
- **Secret Manager:** $0.06/month per secret
- **Artifact Registry:** $0.10/month storage
- **Total:** **~$0.50-2/month**

---

## Next Steps

1. ✅ Review this plan
2. ⏭️ Start with Phase 1 - Create Dockerfile
3. ⏭️ Test locally before cloud deployment
4. ⏭️ Deploy incrementally, test each phase

---

## Rollback Plan

If deployment fails:
1. Revert to local cron job temporarily
2. Debug cloud deployment issues
3. Check logs: `gcloud logging read`
4. Delete and recreate resources if needed

---

**Ready to start? Let's begin with Phase 1!**
