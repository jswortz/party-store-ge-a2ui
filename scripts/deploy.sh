#!/usr/bin/env bash
# One-line remote deploy for the Party Store A2UI agent.
# Clones the repo, deploys to Cloud Run, and registers the agent in Gemini Enterprise.
#
# Run directly from GitHub:
#   curl -fsSL https://raw.githubusercontent.com/jswortz/party-store-ge-a2ui/main/scripts/deploy.sh | bash
#
# Prereqs: git, uv, and gcloud (authenticated: `gcloud auth application-default login`).
set -euo pipefail

REPO_URL="https://github.com/jswortz/party-store-ge-a2ui.git"
WORKDIR="$(mktemp -d)/party-store-ge-a2ui"

echo "==> Cloning ${REPO_URL}"
git clone --depth 1 "${REPO_URL}" "${WORKDIR}"
cd "${WORKDIR}"

echo "==> Deploying to Cloud Run + registering in Gemini Enterprise"
exec bash scripts/deploy_to_ge.sh
