# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A2A HTTP server for the Party Store Supply Chain Agent (Cloud Run target).

Hosts the deterministic PartyStoreExecutor (which emits A2UI v0.8 DataParts tagged
`application/json+a2ui`) as an A2A service so Gemini Enterprise can invoke it. GE cannot invoke A2A
agents on Vertex Agent Runtime, so the agent is served over HTTP on Cloud Run instead.

Mirrors rag_pg_ip/pg_razor_agent/fast_api_app.py (the proven GE + A2UI path): A2AFastAPIApplication,
JSON-RPC, card at /a2a/app/.well-known/agent-card.json, advertising the A2UI extension.
"""
import os

from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentExtension, AgentSkill
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from fastapi import FastAPI
from vertexai.preview.reasoning_engines.templates.a2a import create_agent_card

from app.agent_executor import PartyStoreExecutor
from app.app_utils.typing import Feedback

# App/RPC layout — APP_NAME "app" makes the card URL match the Cloud Run A2A convention:
# https://<svc>/a2a/app/.well-known/agent-card.json
APP_NAME = os.getenv("A2A_APP_NAME", "app")
PORT = int(os.getenv("PORT", "8080"))
# Cloud Run public URL. Defaults to the existing service so the registered card's url stays valid.
APP_URL = os.getenv(
    "APP_URL", "https://party-store-ge-a2ui-679926387543.us-east1.run.app"
).rstrip("/")
RPC_PATH = f"/a2a/{APP_NAME}"
RPC_URL = f"{APP_URL}{RPC_PATH}"

A2UI_EXTENSION_URI = "https://a2ui.org/a2a-extension/a2ui/v0.8"
A2UI_CATALOG_ID = "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"


def _build_agent_card():
    """Agent card advertising the A2UI v0.8 extension (opens the GE canvas)."""
    party_store_skill = AgentSkill(
        id="manage_supply_chain",
        name="Party Store Supply Chain Management",
        description="Manages supply chain operations, queries inventory levels, checks sales forecasts, and creates purchase orders.",
        tags=["supply-chain", "inventory", "forecast", "procurement"],
        examples=[
            "Show inventory status",
            "Show sales forecast for halloween_costume",
            "Order 500 birthday candles",
        ],
    )
    card = create_agent_card(
        agent_name="Party Store Supply Chain Agent",
        description="AI Agent that assists with supply chain planning, monitoring stock levels, analyzing demand, and purchasing inventory.",
        skills=[party_store_skill],
        streaming=False,
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain", "application/json"],
    )
    card.capabilities = AgentCapabilities(
        streaming=False,
        extensions=[
            AgentExtension(
                uri=A2UI_EXTENSION_URI,
                description="Ability to render A2UI",
                required=False,
                params={
                    "supportedCatalogIds": [A2UI_CATALOG_ID],
                    # The forecast screen uses a custom VegaChart component not in the standard
                    # catalog; allow inline catalogs so GE accepts it.
                    "acceptsInlineCatalogs": True,
                },
            )
        ],
    )
    # GE/Cloud Run A2A speaks JSON-RPC at the rpc_url (matches A2AFastAPIApplication).
    card.url = RPC_URL
    card.preferred_transport = "JSONRPC"
    return card


_agent_card = _build_agent_card()
_request_handler = DefaultRequestHandler(
    agent_executor=PartyStoreExecutor(),
    task_store=InMemoryTaskStore(),
)

app = FastAPI(
    title="Party Store Supply Chain Agent",
    description="A2A server hosting the deterministic A2UI Party Store agent.",
)

_a2a_app = A2AFastAPIApplication(agent_card=_agent_card, http_handler=_request_handler)
_a2a_app.add_routes_to_app(
    app,
    agent_card_url=f"{RPC_PATH}{AGENT_CARD_WELL_KNOWN_PATH}",
    rpc_url=RPC_PATH,
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback."""
    import logging

    logging.getLogger(__name__).info("feedback: %s", feedback.model_dump())
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
