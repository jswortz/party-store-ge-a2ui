# Party Store Supply Chain Agent

A multi-agent supply chain optimization assistant powered by the Google Agent Development Kit (ADK) and A2UI v0.8.

The agent helps store managers query current inventory levels, inspect sales forecasts with interactive Vega charts, and automatically place purchase orders via sub-agent delegation.

---

## Project Structure

```
party-store-ge-a2ui/
├── app/                        # Core agent code
│   ├── agent.py                # Agent & Sub-agent definitions and prompts
│   ├── tools.py                # BigQuery tools & A2UI layout generation
│   └── ui_examples/            # A2UI Layout spec files (v0.8 format)
├── scratch/
│   ├── test_api.py             # 3-turn async API integration test script
│   └── setup_bigquery_tables.py # Helper script to populate mock BQ tables
├── agents.md                   # System design & Agent orchestration docs
├── README.md                   # Setup and usage guide (this file)
└── pyproject.toml              # Project dependencies
```

---

## Prerequisites

Ensure you have the following installed:
1. **uv**: Fast Python package manager ([Install](https://docs.astral.sh/uv/getting-started/installation/))
2. **google-agents-cli**: installed with `uv tool install google-agents-cli`
3. **gcloud SDK**: authenticated to your Google Cloud project ([Install](https://cloud.google.com/sdk/docs/install))

---

## Getting Started

### 1. Configure GCP Project

Ensure your active gcloud project is set correctly:
```bash
gcloud config set project wortz-project-352116
```

Ensure you have authenticated your application default credentials (ADC):
```bash
gcloud auth application-default login
```

### 2. Install Dependencies

Install all dependencies in the local virtual environment:
```bash
agents-cli install
```

### 3. Initialize Mock BigQuery Data

Run the helper script to create the `party_store` dataset and populate the `shipments` and `orders` tables in BigQuery:
```bash
uv run scratch/setup_bigquery_tables.py
```

---

## Running the Agent

### Option A: Local Dev UI (Playground)

Start the local web UI to interactively chat with the agent and view the rendered A2UI components:
```bash
agents-cli playground
```
Once the server starts, open the Dev UI URL in your browser:
👉 [http://127.0.0.1:8000/dev-ui/?app=app](http://127.0.0.1:8000/dev-ui/?app=app)

### Option B: Programmatic Integration Test

Run the pre-configured 3-turn async test client to simulate a full conversation flow against the local FastAPI server:
```bash
uv run scratch/test_api.py
```

---

## Interactive Demo Script

When testing the agent (either manually in the Playground UI or watching the output of `test_api.py`), use the following sequential prompts to run through the full supply chain workflow:

1. **Query Inventory Status**
   - **Prompt:** `Show inventory status`
   - **Expected Output:** The agent responds with a text summary of current stock and displays the **Inventory Dashboard** showing a list of items and their stock status.
2. **Inspect Sales Forecast**
   - **Prompt:** `Show sales forecast for halloween_skeleton`
   - **Expected Output:** The agent responds with forecast numbers and displays the **Sales Forecast Chart** (a Vega-Lite line chart showing actuals vs projections).
3. **Place Purchase Order (Delegated)**
   - **Prompt:** `Order 300 halloween_skeletons`
   - **Expected Output:** The parent agent delegates the order to the `procurement_agent` sub-agent. The sub-agent places the order, returns a text confirmation with PO details, and displays the **Purchase Order Confirmation Card**.

---

## Architecture & System Design

For a deep dive into the sub-agent delegation workflow and the Python-driven A2UI rendering architecture, refer to the [agents.md](agents.md) documentation.
