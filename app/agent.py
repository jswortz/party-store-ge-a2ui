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

# Import tools
from app.tools import query_inventory_status, get_sales_forecast, create_purchase_order, send_a2ui_json_to_client

# Catalog configurations are handled in app/a2ui_config.py

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
When you call `create_purchase_order`, it will return the purchase order details and a key `a2ui_key`.
You MUST call `send_a2ui_json_to_client` passing the exact value of `a2ui_key` to the `a2ui_json` argument.
Finally, summarize the purchase order details (PO ID, product, quantity, delivery date) for the user in a friendly text message.
""",
    tools=[create_purchase_order, send_a2ui_json_to_client],
)

# Supply Chain Agent
supply_chain_agent = Agent(
    name="supply_chain_agent",
    model=model_flash,
    instruction="""You are a Supply Chain Optimization Agent.
You help users manage inventory, forecast demand, and identify low stock items.
You have access to the following tools:
1. `query_inventory_status`: Use this to get the current inventory levels. It returns a key `a2ui_key`.
2. `get_sales_forecast`: Use this to get sales forecast for a product. It returns a key `a2ui_key`.
3. `procurement_agent`: A delegated agent that can create purchase orders.

Your workflow:
- When the user asks to see inventory or dashboard, call `query_inventory_status`. You MUST then call `send_a2ui_json_to_client` passing the exact value of `a2ui_key` to the `a2ui_json` argument.
- When the user asks about a forecast, call `get_sales_forecast`. You MUST then call `send_a2ui_json_to_client` passing the exact value of `a2ui_key` to the `a2ui_json` argument.
- If inventory is low or forecast shows high seasonal demand (especially for halloween items in Sep/Oct), warn the user and suggest ordering more.
- If the user agrees to order more, delegate to `procurement_agent`. Do NOT call `create_purchase_order` directly, always delegate.
- Provide a friendly, concise summary of the data in text alongside your UI calls.
""",
    sub_agents=[procurement_agent],
    tools=[query_inventory_status, get_sales_forecast, send_a2ui_json_to_client],
)
from app.a2ui_plugin import A2uiRendererPlugin

app = App(
    root_agent=supply_chain_agent,
    name="party_store_agent",
    plugins=[A2uiRendererPlugin()],
)
