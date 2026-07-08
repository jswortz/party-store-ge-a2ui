#!/bin/bash
# Scripts to deploy the Party Store Supply Chain Agent to Vertex AI Agent Runtime
# and register it in the Gemini Enterprise App.
#
# Exit immediately if a command exits with a non-zero status.
set -e

PROJECT_ID="wortz-project-352116"
REGION="us-east1"
GE_APP_ID="projects/wortz-project-352116/locations/global/collections/default_collection/engines/gemini-enterprise-17634901_1763490144996"
DISPLAY_NAME="Party Store Supply Chain Agent"

echo "=== 1. Enabling Required GCP APIs ==="
gcloud services enable \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project="${PROJECT_ID}"

echo "=== 2. Deploying Agent to Vertex AI Agent Runtime ==="
# Deploys as a Reasoning Engine. This will automatically compile and build
# the Docker image using Cloud Build, and output 'deployment_metadata.json'.
agents-cli deploy \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --deployment-target=agent_runtime \
  --no-confirm-project

echo "=== 3. Registering Agent with Gemini Enterprise ==="
# Auto-detects the newly deployed reasoning engine ID from 'deployment_metadata.json'
# and registers it natively with the Gemini Enterprise App.
agents-cli publish gemini-enterprise \
  --gemini-enterprise-app-id="${GE_APP_ID}" \
  --display-name="${DISPLAY_NAME}"

echo "=== Deployment & Publishing Completed Successfully! ==="
