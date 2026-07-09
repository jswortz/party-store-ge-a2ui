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
import logging
import os
from typing import Any

import vertexai
from dotenv import load_dotenv
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.runners import Runner
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.cloud import logging as google_cloud_logging
from vertexai.preview.reasoning_engines import A2aAgent
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentExtension
from vertexai.preview.reasoning_engines.templates.a2a import create_agent_card

from app.agent import supply_chain_agent
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

# Load environment variables from .env file at runtime
load_dotenv()

gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

def get_runner() -> Runner:
    artifact_service = (
        GcsArtifactService(bucket_name=logs_bucket_name)
        if logs_bucket_name
        else InMemoryArtifactService()
    )
    session_service = (
        VertexAiSessionService(agent_engine_id=os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID"))
        if os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID")
        else InMemorySessionService()
    )
    # Crucially, import and register A2uiRendererPlugin
    from app.a2ui_plugin import A2uiRendererPlugin
    
    return Runner(
        app_name="party_store_agent",
        agent=supply_chain_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        plugins=[A2uiRendererPlugin()],
        auto_create_session=True,
    )

class A2aAgentEngineApp(A2aAgent):
    def set_up(self) -> None:
        """Initialize the agent engine app with logging and telemetry."""
        vertexai.init()
        setup_telemetry()
        super().set_up()
        logging.basicConfig(level=logging.INFO)
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)
        if gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent."""
        operations = super().register_operations()
        operations[""] = [*operations.get("", []), "query", "register_feedback"]
        operations["stream"] = [*operations.get("stream", []), "stream"]
        return operations

    async def query(self, text: str, **kwargs) -> str:
        """Standard query method called by the Vertex AI Reasoning Engine Playground."""
        agent_executor = self._tmpl_attrs.get("agent_executor")
        runner = await agent_executor._resolve_runner()
        
        from google.genai import types
        
        new_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)]
        )
        
        response_text_parts = []
        async for event in runner.run_async(
            new_message=new_message,
            user_id=kwargs.get("user_id", "playground-user"),
            session_id=kwargs.get("session_id", "playground-session"),
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response_text_parts.extend([p.text for p in event.content.parts if p.text])
        return "".join(response_text_parts)

    async def stream(self, text: str, **kwargs):
        """Standard stream method called by the Vertex AI Reasoning Engine Playground (streaming mode)."""
        response_text = await self.query(text, **kwargs)
        yield response_text


party_store_skill = AgentSkill(
    id="manage_supply_chain",
    name="Party Store Supply Chain Management",
    description="Manages supply chain operations, queries inventory levels, checks sales forecasts, and creates purchase orders.",
    tags=["supply-chain", "inventory", "forecast", "procurement"],
    examples=[
        "Show inventory status",
        "Show sales forecast for halloween_costume",
        "Order 500 birthday candles"
    ]
)

cc_agent_card = create_agent_card(
    agent_name="Party Store Supply Chain Agent",
    description="AI Agent that assists with supply chain planning, monitoring stock levels, analyzing demand, and purchasing inventory.",
    skills=[party_store_skill],
    streaming=False,
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
)

# Inject A2UI capability extensions into the card (so that Gemini Enterprise opens the canvas side panel)
cc_agent_card.capabilities = AgentCapabilities(
    streaming=False,
    extensions=[
        AgentExtension(
            uri="https://a2ui.org/a2a-extension/a2ui/v0.8",
            description="Ability to render A2UI",
            required=False,
            params={
                "supportedCatalogIds": [
                    "https://a2ui.org/specification/v0_8/standard_catalog_definition.json"
                ]
            }
        )
    ]
)

from google.adk.a2a.executor.config import A2aAgentExecutorConfig
from a2ui.adk.a2a.part_converter import A2uiPartConverter
from app.a2ui_config import catalog

executor_config = A2aAgentExecutorConfig(
    gen_ai_part_converter=A2uiPartConverter(a2ui_catalog=catalog).convert
)

agent_runtime = A2aAgentEngineApp(
    agent_card=cc_agent_card,
    agent_executor_builder=A2aAgentExecutor,
    agent_executor_kwargs={
        "runner": get_runner,
        "config": executor_config,
    },
)

