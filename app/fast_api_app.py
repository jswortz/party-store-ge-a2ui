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
import os

import google.auth
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging

# Manual A2A imports
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotificationConfigStore, InMemoryTaskStore
from a2a.types import AgentCard
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

setup_telemetry()
_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In-memory session configuration - no persistent storage
session_service_uri = None

artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=True,
    a2a=False, # Disabled to avoid SDK bug
)

# Manual A2A Setup
def create_a2a_runner_loader(app_name: str):
    async def _get_a2a_runner_async():
        from google.adk.cli.utils.agent_loader import AgentLoader
        from google.adk.runners import Runner
        from google.adk.cli.utils.service_factory import (
            create_session_service_from_options,
            create_artifact_service_from_options,
            create_memory_service_from_options,
        )
        from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
        from google.adk.apps.app import App
        from google.adk.agents.base_agent import BaseAgent

        loader = AgentLoader(AGENT_DIR)
        agent_or_app = loader.load_agent(app_name)

        if isinstance(agent_or_app, App):
             agentic_app = agent_or_app
        elif isinstance(agent_or_app, BaseAgent):
             agentic_app = App(name=app_name, root_agent=agent_or_app)
        else:
             agentic_app = App(name=app_name, root_agent=agent_or_app)

        session_service = create_session_service_from_options(base_dir=AGENT_DIR, use_local_storage=False)
        artifact_service = create_artifact_service_from_options(base_dir=AGENT_DIR, use_local_storage=False)
        memory_service = create_memory_service_from_options(base_dir=AGENT_DIR)
        credential_service = InMemoryCredentialService()

        return Runner(
            app=agentic_app,
            app_name=app_name,
            artifact_service=artifact_service,
            session_service=session_service,
            memory_service=memory_service,
            credential_service=credential_service,
            auto_create_session=True,
        )
    return _get_a2a_runner_async

try:
    print("DEBUG: Setting up manual A2A...", flush=True)
    agent_json_path = os.path.join(AGENT_DIR, "app", "agent.json")
    with open(agent_json_path, "r", encoding="utf-8") as f:
        import json
        data = json.load(f)
        agent_card = AgentCard(**data)

    agent_executor = A2aAgentExecutor(
        runner=create_a2a_runner_loader("app"),
    )

    a2a_task_store = InMemoryTaskStore()
    push_config_store = InMemoryPushNotificationConfigStore()
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=a2a_task_store,
        push_config_store=push_config_store,
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    routes = a2a_app.routes(
        rpc_url="/a2a/app",
        agent_card_url=f"/a2a/app{AGENT_CARD_WELL_KNOWN_PATH}",
    )

    for new_route in routes:
        app.router.routes.append(new_route)
    print("DEBUG: Manual A2A setup complete!", flush=True)
except Exception as e:
    print(f"DEBUG: Failed to setup manual A2A: {e}", flush=True)
    import traceback
    traceback.print_exc()

app.title = "party-store-temp"
app.description = "API for interacting with the Agent party-store-temp"

@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
