# Deploying the Party Store Agent to Gemini Enterprise

This is the **actual, working** deployment path (verified end-to-end). It supersedes any older
"Agent Runtime / Reasoning Engine" instructions.

## Why Cloud Run (not Agent Runtime)

**Gemini Enterprise (GE) cannot invoke A2A agents hosted on Vertex Agent Runtime / Reasoning Engine.**
When GE is pointed at an Agent Runtime endpoint, the correctly-built A2UI `DataPart` is degraded to a
`text/plain` blob and the GE canvas renders nothing. The A2UI screens only render when the agent is
served as an **A2A HTTP service on Cloud Run** and GE is registered against that Cloud Run URL.

The GE-facing entrypoint is `app/fast_api_app.py` — a deterministic A2A server
(`A2AFastAPIApplication`, JSON-RPC at `/a2a/app`) whose `PartyStoreExecutor` emits each A2UI command as
a `DataPart` tagged `metadata.mimeType = application/json+a2ui`. `agent_runtime_app.py` is retained for
the Reasoning Engine Playground only — it is NOT the GE path.

## Reference values

| Thing | Value |
|---|---|
| Project | `wortz-project-352116` (number `679926387543`) |
| Region | `us-east1` |
| Cloud Run service | `party-store-ge-a2ui` |
| Service URL | `https://party-store-ge-a2ui-679926387543.us-east1.run.app` |
| A2A endpoint | `…run.app/a2a/app` (card at `/a2a/app/.well-known/agent-card.json`) |
| Runtime service account | `679926387543-compute@developer.gserviceaccount.com` |
| BigQuery dataset | `wortz-project-352116.party_store` (`orders`, `shipments`) |
| GE engine (app) id | `gemini-enterprise-17634901_1763490144996` |
| GE agent id | `10192074070999086566` |

## Prerequisites

- `gcloud` authenticated with ADC: `gcloud auth application-default login`
- Project set: `gcloud config set project wortz-project-352116`
- `.python-version` present and pinned to **3.13** (see Troubleshooting — the buildpack offers only
  3.13/3.14 and `litellm` requires `<3.14`).

## Step 1 — Deploy to Cloud Run

```bash
gcloud run deploy party-store-ge-a2ui \
  --source . \
  --region us-east1 \
  --project wortz-project-352116 \
  --allow-unauthenticated \
  --update-env-vars APP_URL=https://party-store-ge-a2ui-679926387543.us-east1.run.app
```

- `--source .` uses Cloud Buildpacks with the `Procfile` (`uvicorn app.fast_api_app:app`).
- `--allow-unauthenticated` is required so GE's network can reach the A2A endpoint.
- `APP_URL` makes the served agent card advertise the public Cloud Run `/a2a/app` URL.

## Step 2 — BigQuery access for the runtime service account

The tools query `wortz-project-352116.party_store` on every request. The Cloud Run runtime SA needs
read + job permissions (the default compute SA usually already has broad access; grant explicitly if a
request returns a permissions error):

```bash
SA=679926387543-compute@developer.gserviceaccount.com
gcloud projects add-iam-policy-binding wortz-project-352116 \
  --member="serviceAccount:${SA}" --role="roles/bigquery.dataViewer"
gcloud projects add-iam-policy-binding wortz-project-352116 \
  --member="serviceAccount:${SA}" --role="roles/bigquery.jobUser"
```

## Step 3 — Register / update the agent in Gemini Enterprise

The GE agent's registered card `url` must be the Cloud Run `/a2a/app` endpoint (NOT a
`reasoningEngines/.../a2a` URL). Fetch the deployed card and PATCH the registration:

```bash
uv run python scripts/register_cloud_run_agent.py
```

This fetches `…run.app/a2a/app/.well-known/agent-card.json` (JSONRPC transport, A2UI v0.8 extension
with `acceptsInlineCatalogs`) and PATCHes `a2aAgentDefinition.jsonAgentCard` on GE agent
`10192074070999086566` via the Discovery Engine API. To list/inspect existing registrations first:
`uv run python scripts/list_registered_agents.py`.

## Step 4 — Verify

```bash
BASE=https://party-store-ge-a2ui-679926387543.us-east1.run.app

# 1. Agent card advertises the A2UI extension + JSONRPC + Cloud Run url
curl -s $BASE/a2a/app/.well-known/agent-card.json | python3 -m json.tool

# 2. A2A message/send returns an artifact 'response' whose DataParts are tagged
#    application/json+a2ui and contain a WebFrameSrcdoc panel (not a text/plain blob)
```

Then, in the [GE console](https://console.cloud.google.com/gemini-enterprise/locations/global/engines/gemini-enterprise-17634901_1763490144996/overview/dashboard?project=wortz-project-352116),
run the three demo prompts and confirm the canvas renders:
- `Show inventory status` → branded inventory dashboard (KPI tiles + stock bars)
- `Show sales forecast for halloween_costume` → forecast area chart
- `Order 500 birthday candles` → purchase-order receipt

## One-shot script

From a local checkout — `./scripts/deploy_to_ge.sh` runs Steps 1 + 3 (enable APIs → Cloud Run
deploy → GE re-registration).

**Run directly from GitHub (clones + deploys + registers):**

```bash
curl -fsSL https://raw.githubusercontent.com/jswortz/party-store-ge-a2ui/main/scripts/deploy.sh | bash
```

Requires `git`, `uv`, and an authenticated `gcloud` (`gcloud auth application-default login`).

## Troubleshooting

- **Build fails: `litellm requires Python >=3.10,<3.14` / `version 3.12 not satisfied`.** The
  buildpack only offers Python 3.13/3.14. Pin `.python-version` to `3.13` (3.14 breaks `litellm`; 3.12
  isn't available in the builder).
- **GE canvas is empty but the agent replies with text.** The registered card is pointing at the wrong
  endpoint (Agent Runtime) or an old revision. Re-run Step 3 so GE targets the Cloud Run `/a2a/app`
  URL, and confirm `message/send` returns `DataPart`s tagged `application/json+a2ui` (see Step 4).
- **`/healthz` returns a Google 404 but `/a2a/app` works.** Cosmetic Cloud Run proxy quirk; the A2A
  endpoints are what GE uses.
- **Iterate on the visuals.** The demo-impact critic flywheel lives in `scripts/ui_critic/`
  (`uv run --with playwright python scripts/ui_critic/flywheel.py`).
