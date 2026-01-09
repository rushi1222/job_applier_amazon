#!/bin/bash

# Google Cloud Deployment Script for Job Scraper
# This script deploys the job scraper to Cloud Run Jobs with secrets from Secret Manager

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="job-scraper"
REPOSITORY_NAME="job-scraper-repo"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${SERVICE_NAME}:latest"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Job Scraper - Google Cloud Deployment${NC}"
echo -e "${GREEN}======================================${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found. Please install it first.${NC}"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Prompt for project ID if not set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}Enter your Google Cloud Project ID:${NC}"
    read PROJECT_ID
fi

echo -e "\n${GREEN}Using Project ID: ${PROJECT_ID}${NC}"
echo -e "${GREEN}Using Region: ${REGION}${NC}\n"

# Set the project
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}Enabling required Google Cloud APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com

echo -e "${GREEN}✓ APIs enabled${NC}\n"

# Create secrets in Secret Manager
echo -e "${YELLOW}Setting up secrets in Secret Manager...${NC}"

# Load .env file
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with your credentials."
    exit 1
fi

# Read .env file properly (handle spaces in values)
export $(grep -v '^#' .env | xargs -0)

# Create GMAIL_SENDER_EMAIL secret
if gcloud secrets describe GMAIL_SENDER_EMAIL --project=${PROJECT_ID} &>/dev/null; then
    echo "Secret GMAIL_SENDER_EMAIL already exists, updating..."
    echo -n "${GMAIL_SENDER_EMAIL}" | gcloud secrets versions add GMAIL_SENDER_EMAIL --data-file=-
else
    echo "Creating secret GMAIL_SENDER_EMAIL..."
    echo -n "${GMAIL_SENDER_EMAIL}" | gcloud secrets create GMAIL_SENDER_EMAIL \
        --data-file=- \
        --replication-policy="automatic"
fi

# Create GMAIL_SENDER_PASSWORD secret
if gcloud secrets describe GMAIL_SENDER_PASSWORD --project=${PROJECT_ID} &>/dev/null; then
    echo "Secret GMAIL_SENDER_PASSWORD already exists, updating..."
    echo -n "${GMAIL_SENDER_PASSWORD}" | gcloud secrets versions add GMAIL_SENDER_PASSWORD --data-file=-
else
    echo "Creating secret GMAIL_SENDER_PASSWORD..."
    echo -n "${GMAIL_SENDER_PASSWORD}" | gcloud secrets create GMAIL_SENDER_PASSWORD \
        --data-file=- \
        --replication-policy="automatic"
fi

# Create RECIPIENT_EMAIL secret
if gcloud secrets describe RECIPIENT_EMAIL --project=${PROJECT_ID} &>/dev/null; then
    echo "Secret RECIPIENT_EMAIL already exists, updating..."
    echo -n "${RECIPIENT_EMAIL}" | gcloud secrets versions add RECIPIENT_EMAIL --data-file=-
else
    echo "Creating secret RECIPIENT_EMAIL..."
    echo -n "${RECIPIENT_EMAIL}" | gcloud secrets create RECIPIENT_EMAIL \
        --data-file=- \
        --replication-policy="automatic"
fi

echo -e "${GREEN}✓ Secrets created/updated${NC}\n"

# Create Artifact Registry repository
echo -e "${YELLOW}Setting up Artifact Registry...${NC}"
if gcloud artifacts repositories describe ${REPOSITORY_NAME} --location=${REGION} &>/dev/null; then
    echo "Repository already exists"
else
    gcloud artifacts repositories create ${REPOSITORY_NAME} \
        --repository-format=docker \
        --location=${REGION} \
        --description="Docker repository for job scraper"
    echo -e "${GREEN}✓ Repository created${NC}"
fi

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev

echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build --platform linux/amd64 -t ${IMAGE_NAME} .
echo -e "${GREEN}✓ Docker image built${NC}\n"

echo -e "${YELLOW}Pushing image to Artifact Registry...${NC}"
docker push ${IMAGE_NAME}
echo -e "${GREEN}✓ Image pushed${NC}\n"

# Deploy Cloud Run Job
echo -e "${YELLOW}Deploying Cloud Run Job...${NC}"

# Get the project number for service account
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Create or update the Cloud Run Job
gcloud run jobs deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --max-retries 2 \
    --task-timeout 15m \
    --memory 2Gi \
    --cpu 1 \
    --set-secrets=GMAIL_SENDER_EMAIL=GMAIL_SENDER_EMAIL:latest,GMAIL_SENDER_PASSWORD=GMAIL_SENDER_PASSWORD:latest,RECIPIENT_EMAIL=RECIPIENT_EMAIL:latest \
    --execute-now=false

echo -e "${GREEN}✓ Cloud Run Job deployed${NC}\n"

# Grant Secret Manager access to the service account
echo -e "${YELLOW}Granting secret access to service account...${NC}"
for secret in GMAIL_SENDER_EMAIL GMAIL_SENDER_PASSWORD RECIPIENT_EMAIL; do
    gcloud secrets add-iam-policy-binding ${secret} \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet || true
done
echo -e "${GREEN}✓ Permissions granted${NC}\n"

# Test manual execution
echo -e "${YELLOW}Testing manual execution...${NC}"
echo "You can run the job manually with:"
echo "  gcloud run jobs execute ${SERVICE_NAME} --region ${REGION}"
echo ""

# Set up Cloud Scheduler
echo -e "${YELLOW}Do you want to set up Cloud Scheduler now? (y/n)${NC}"
read -r setup_scheduler

if [ "$setup_scheduler" = "y" ]; then
    SCHEDULER_JOB_NAME="${SERVICE_NAME}-schedule"
    
    # Check if scheduler job exists
    if gcloud scheduler jobs describe ${SCHEDULER_JOB_NAME} --location=${REGION} &>/dev/null; then
        echo "Scheduler job already exists, updating..."
        gcloud scheduler jobs update http ${SCHEDULER_JOB_NAME} \
            --location ${REGION} \
            --schedule "*/30 9-19 * * *" \
            --time-zone "America/Chicago" \
            --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${SERVICE_NAME}:run" \
            --http-method POST \
            --oauth-service-account-email ${SERVICE_ACCOUNT}
    else
        echo "Creating scheduler job..."
        gcloud scheduler jobs create http ${SCHEDULER_JOB_NAME} \
            --location ${REGION} \
            --schedule "*/30 9-19 * * *" \
            --time-zone "America/Chicago" \
            --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${SERVICE_NAME}:run" \
            --http-method POST \
            --oauth-service-account-email ${SERVICE_ACCOUNT}
    fi
    
    echo -e "${GREEN}✓ Cloud Scheduler configured${NC}"
    echo -e "${GREEN}  Schedule: Every 30 minutes from 9 AM to 7 PM CT${NC}\n"
fi

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "Cloud Run Job URL:"
echo -e "https://console.cloud.google.com/run/jobs/details/${REGION}/${SERVICE_NAME}?project=${PROJECT_ID}"
echo ""
echo -e "Useful commands:"
echo -e "  ${YELLOW}# Run job manually${NC}"
echo -e "  gcloud run jobs execute ${SERVICE_NAME} --region ${REGION}"
echo ""
echo -e "  ${YELLOW}# View logs${NC}"
echo -e "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${SERVICE_NAME}\" --limit 50 --format json"
echo ""
echo -e "  ${YELLOW}# Update secrets${NC}"
echo -e "  echo -n 'new-value' | gcloud secrets versions add SECRET_NAME --data-file=-"
echo ""
