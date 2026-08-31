#!/bin/bash
set -e

PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="asia-south1" # Mumbai / Pune region for low latency in India
SERVICE_NAME="job-agent-backend"

echo "======================================================="
echo " Deploying ${SERVICE_NAME} to Cloud Run in ${REGION}..."
echo "======================================================="

gcloud run deploy ${SERVICE_NAME} \
    --source=./backend \
    --project=${PROJECT_ID} \
    --region=${REGION} \
    --platform=managed \
    --memory=2Gi \
    --cpu=2 \
    --min-instances=1 \
    --max-instances=10 \
    --timeout=300 \
    --session-affinity \
    --allow-unauthenticated \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GEMINI_MODEL=gemini-2.5-flash,GCP_REGION=${REGION}"

echo "Deployment completed successfully."
