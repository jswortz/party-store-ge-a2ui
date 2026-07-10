#!/bin/bash
# Deploy the Party Store Supply Chain Agent as an A2A service on Cloud Run and register it
# in Gemini Enterprise pointing at the Cloud Run URL.
#
# NOTE: Gemini Enterprise CANNOT invoke A2A agents on Vertex Agent Runtime / Reasoning Engine —
# that path degrades the A2UI DataPart to text and the canvas renders nothing. The working GE path
# is Cloud Run (app/fast_api_app.py). See DEPLOY.md for the full runbook + troubleshooting.
#
# Exit immediately if a command exits with a non-zero status.
set -e

PROJECT_ID="wortz-project-352116"
REGION="us-east1"
SERVICE="party-store-ge-a2ui"
APP_URL="https://party-store-ge-a2ui-679926387543.us-east1.run.app"

echo "=== 1. Enabling required GCP APIs ==="
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  discoveryengine.googleapis.com \
  --project="${PROJECT_ID}"

echo "=== 2. Deploying A2A server to Cloud Run ==="
# Buildpacks use the Procfile (uvicorn app.fast_api_app:app). Requires .python-version=3.13
# (the builder offers only 3.13/3.14 and litellm requires <3.14). --allow-unauthenticated is
# required so GE's network can reach the /a2a/app endpoint.
gcloud run deploy "${SERVICE}" \
  --source . \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated \
  --update-env-vars "APP_URL=${APP_URL}" \
  --quiet

echo "=== 3. Registering the Cloud Run card in Gemini Enterprise ==="
# Fetches the deployed /a2a/app card (JSONRPC + A2UI v0.8 extension) and PATCHes the GE agent
# registration so GE targets the Cloud Run URL. See scratch/register_cloud_run_agent.py.
uv run python scratch/register_cloud_run_agent.py

echo "=== Deployment complete. Verify per DEPLOY.md (Step 4). ==="
echo "Service URL: ${APP_URL}/a2a/app"
