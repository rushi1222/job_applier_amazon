# Google Cloud Deployment Guide

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed ([Installation guide](https://cloud.google.com/sdk/docs/install))
3. **Docker** installed and running
4. **.env file** with your credentials (GMAIL_SENDER_EMAIL, GMAIL_SENDER_PASSWORD, RECIPIENT_EMAIL)

## Quick Start

### 1. Install gcloud CLI (if not installed)

```bash
# macOS
brew install google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install
```

### 2. Authenticate with Google Cloud

```bash
gcloud auth login
gcloud auth application-default login
```

### 3. Set Your Project ID

```bash
# Create a new project or use existing
export GCP_PROJECT_ID="your-project-id"

# Or let the script prompt you
```

### 4. Run Deployment Script

```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
- ✅ Enable required Google Cloud APIs
- ✅ Create secrets in Secret Manager from your `.env` file
- ✅ Create Artifact Registry repository
- ✅ Build and push Docker image
- ✅ Deploy Cloud Run Job
- ✅ Set up IAM permissions
- ✅ (Optional) Configure Cloud Scheduler

## Manual Deployment Steps

If you prefer manual deployment, follow these steps:

### Step 1: Enable APIs

```bash
gcloud services enable \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com
```

### Step 2: Create Secrets

```bash
# Load your .env file
source .env

# Create secrets
echo -n "${GMAIL_SENDER_EMAIL}" | gcloud secrets create GMAIL_SENDER_EMAIL --data-file=-
echo -n "${GMAIL_SENDER_PASSWORD}" | gcloud secrets create GMAIL_SENDER_PASSWORD --data-file=-
echo -n "${RECIPIENT_EMAIL}" | gcloud secrets create RECIPIENT_EMAIL --data-file=-
```

### Step 3: Create Artifact Registry

```bash
gcloud artifacts repositories create job-scraper-repo \
    --repository-format=docker \
    --location=us-central1
```

### Step 4: Build and Push Image

```bash
PROJECT_ID="your-project-id"
REGION="us-central1"

# Configure Docker
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build image for linux/amd64 (Cloud Run requirement)
docker build --platform linux/amd64 \
    -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/job-scraper-repo/job-scraper:latest .

# Push to registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/job-scraper-repo/job-scraper:latest
```

### Step 5: Deploy Cloud Run Job

```bash
gcloud run jobs deploy job-scraper \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/job-scraper-repo/job-scraper:latest \
    --region us-central1 \
    --max-retries 2 \
    --task-timeout 15m \
    --memory 2Gi \
    --cpu 1 \
    --set-secrets=GMAIL_SENDER_EMAIL=GMAIL_SENDER_EMAIL:latest,GMAIL_SENDER_PASSWORD=GMAIL_SENDER_PASSWORD:latest,RECIPIENT_EMAIL=RECIPIENT_EMAIL:latest
```

### Step 6: Grant Secret Access

```bash
# Get project number
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")

# Grant access to secrets
for secret in GMAIL_SENDER_EMAIL GMAIL_SENDER_PASSWORD RECIPIENT_EMAIL; do
    gcloud secrets add-iam-policy-binding ${secret} \
        --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
done
```

### Step 7: Set Up Cloud Scheduler

```bash
gcloud scheduler jobs create http job-scraper-schedule \
    --location us-central1 \
    --schedule "*/30 9-19 * * *" \
    --time-zone "America/Chicago" \
    --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/job-scraper:run" \
    --http-method POST \
    --oauth-service-account-email ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com
```

## Testing

### Test Manual Execution

```bash
gcloud run jobs execute job-scraper --region us-central1
```

### View Logs

```bash
# Recent logs
gcloud logging read "resource.type=cloud_run_job" --limit 50

# Job-specific logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=job-scraper" --limit 50 --format json
```

## Updating

### Update Secrets

```bash
echo -n "new-email@gmail.com" | gcloud secrets versions add GMAIL_SENDER_EMAIL --data-file=-
```

### Update Code and Redeploy

```bash
# Make your code changes, then:
./deploy.sh
```

### Update Schedule

```bash
gcloud scheduler jobs update http job-scraper-schedule \
    --location us-central1 \
    --schedule "*/15 9-19 * * *"  # Every 15 minutes instead of 30
```

## Cost Optimization (Free Tier)

Cloud Run Jobs free tier includes:
- **2 million requests/month**
- **400,000 GB-seconds of compute time**
- **200,000 vCPU-seconds**

With our setup (every 30 min, 9am-7pm = ~20 executions/day):
- **Monthly executions**: ~600
- **Compute time**: ~600 executions × 2 minutes = 1,200 minutes = 2,400 GB-seconds
- **Cost**: **$0/month** (well within free tier)

Cloud Scheduler free tier:
- **3 jobs free** per month
- **Cost**: **$0/month**

Secret Manager:
- **$0.06/secret/month** × 3 secrets = **$0.18/month**

**Total Monthly Cost: ~$0.20**

## Monitoring

### Set Up Alerts

```bash
# Create alert for job failures (optional)
# Visit: https://console.cloud.google.com/monitoring/alerting
```

### Check Job Status

```bash
# List executions
gcloud run jobs executions list --job job-scraper --region us-central1

# Describe specific execution
gcloud run jobs executions describe EXECUTION_ID --region us-central1
```

## Troubleshooting

### Job fails to start
- Check logs: `gcloud logging read "resource.type=cloud_run_job" --limit 20`
- Verify secrets are accessible
- Check Docker image was built for `linux/amd64`

### No emails received
- Verify Gmail app password is correct
- Check job completed successfully
- Review application logs for email errors

### Secret access denied
```bash
# Re-grant permissions
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding GMAIL_SENDER_EMAIL \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Useful Commands

```bash
# Run job manually
gcloud run jobs execute job-scraper --region us-central1

# View recent logs
gcloud logging read "resource.type=cloud_run_job" --limit 50

# Pause scheduler
gcloud scheduler jobs pause job-scraper-schedule --location us-central1

# Resume scheduler
gcloud scheduler jobs resume job-scraper-schedule --location us-central1

# Delete everything
gcloud run jobs delete job-scraper --region us-central1
gcloud scheduler jobs delete job-scraper-schedule --location us-central1
gcloud secrets delete GMAIL_SENDER_EMAIL
gcloud secrets delete GMAIL_SENDER_PASSWORD
gcloud secrets delete RECIPIENT_EMAIL
```

## Next Steps

After successful deployment:
1. ✅ Test manual execution to verify everything works
2. ✅ Monitor first few scheduled runs
3. ✅ Set up monitoring alerts (optional)
4. ✅ Add more companies to `companies.yaml`
5. ✅ Enjoy automated job notifications! 🎉
