# ruff: noqa
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
import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import a2ui
from a2ui.schema.catalog import CatalogConfig
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.adk.send_a2ui_to_client_toolset import SendA2uiToClientToolset

# Import tools
from app.tools import query_inventory_status, get_sales_forecast, create_purchase_order

from a2ui.schema.common_modifiers import remove_strict_validation

# A2UI Catalog setup with VegaChart support
def add_vega_chart(schema: dict) -> dict:
    if "components" in schema:
        schema["components"]["VegaChart"] = {
            "type": "object",
            "properties": {
                "spec": {
                    "type": "object",
                    "description": "The Vega-Lite specification for the chart."
                }
            },
            "required": ["spec"]
        }
    return schema

a2ui_path = list(a2ui.__path__)[0]
standard_catalog_path = os.path.join(
    a2ui_path, "assets", "0.8", "standard_catalog_definition.json"
)
catalog_config = CatalogConfig.from_path("standard", standard_catalog_path)
schema_manager = A2uiSchemaManager(
    "0.8",
    catalogs=[catalog_config],
    schema_modifiers=[add_vega_chart, remove_strict_validation]
)
catalog = schema_manager.get_selected_catalog()

# Examples directory
UI_EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_examples")
examples_str = catalog.load_examples(UI_EXAMPLES_DIR, validate=True)

# A2UI Toolset
a2ui_toolset = SendA2uiToClientToolset(
    a2ui_enabled=True,
    a2ui_catalog=catalog,
    a2ui_examples=examples_str,
)

# Model configuration
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-east1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

model_flash = Gemini(
    model="gemini-2.5-flash",
    retry_options=types.HttpRetryOptions(attempts=3),
)

# Procurement Agent
procurement_agent = Agent(
    name="procurement_agent",
    model=model_flash,
    instruction="""You are a Procurement Agent. 
Your job is to create purchase orders for products when requested.
You have access to the `create_purchase_order` tool.
When you call `create_purchase_order`, it will return the purchase order details and a key `a2ui_payload_str`.
You MUST call `send_a2ui_json_to_client` passing the exact value of `a2ui_payload_str` (without modifying it) to the `a2ui_json` argument.
Finally, summarize the purchase order details (PO ID, product, quantity, delivery date) for the user in a friendly text message.
""",
    tools=[create_purchase_order, a2ui_toolset],
)

# Supply Chain Agent
supply_chain_agent = Agent(
    name="supply_chain_agent",
    model=model_flash,
    instruction="""You are a Supply Chain Optimization Agent.
You help users manage inventory, forecast demand, and identify low stock items.
You have access to the following tools:
1. `query_inventory_status`: Use this to get the current inventory levels. It returns a key `a2ui_payload_str`.
2. `get_sales_forecast`: Use this to get sales forecast for a product. It returns a key `a2ui_payload_str`.
3. `procurement_agent`: A delegated agent that can create purchase orders.

Your workflow:
- When the user asks to see inventory or dashboard, call `query_inventory_status`. You MUST then call `send_a2ui_json_to_client` passing the exact value of `a2ui_payload_str` to the `a2ui_json` argument.
- When the user asks about a forecast, call `get_sales_forecast`. You MUST then call `send_a2ui_json_to_client` passing the exact value of `a2ui_payload_str` to the `a2ui_json` argument.
- If inventory is low or forecast shows high seasonal demand (especially for halloween items in Sep/Oct), warn the user and suggest ordering more.
- If the user agrees to order more, delegate to `procurement_agent`. Do NOT call `create_purchase_order` directly, always delegate.
- Provide a friendly, concise summary of the data in text alongside your UI calls.
""",
    sub_agents=[procurement_agent],
    tools=[query_inventory_status, get_sales_forecast, a2ui_toolset],
)

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.events.event import Event
from google.genai import types
import json
from typing import Optional

class A2uiRendererPlugin(BasePlugin):
    """
    A custom plugin that intercepts 'send_a2ui_json_to_client' tool responses
    and converts them to A2UI-compatible A2A parts, wrapping them in 
    `<a2a_datapart_json>` wrappers so that the local Dev UI client renders them.
    """
    def __init__(self, name: str = "a2ui_renderer"):
        super().__init__(name)

    async def on_event_callback(
        self, *, invocation_context, event: Event
    ) -> Optional[Event]:
        if event.content and event.content.parts:
            new_parts = []
            modified = False
            for part in event.content.parts:
                if (
                    part.function_response 
                    and part.function_response.name == "send_a2ui_json_to_client"
                ):
                    response = part.function_response.response or {}
                    a2ui_json_payload = response.get("validated_a2ui_json")
                    if a2ui_json_payload:
                        # Construct the A2A DataPart structure expected by the client
                        data_part = {
                            "kind": "data",
                            "metadata": {
                                "mimeType": "application/json+a2ui"
                            },
                            "data": a2ui_json_payload
                        }
                        
                        # Serialize and wrap in A2A tag
                        part_json = json.dumps(data_part, separators=(',', ':'))
                        wrapped_data = (
                            b"<a2a_datapart_json>" 
                            + part_json.encode('utf-8') 
                            + b"</a2a_datapart_json>"
                        )
                        
                        # Create the new inline_data part
                        new_part = types.Part(
                            inline_data=types.Blob(
                                mime_type="text/plain",
                                data=wrapped_data
                            )
                        )
                        new_parts.append(new_part)
                        modified = True
                        continue
                new_parts.append(part)
            if modified:
                event.content.parts = new_parts
        return event

app = App(
    root_agent=supply_chain_agent,
    name="party_store_agent",
    plugins=[A2uiRendererPlugin()]
)
