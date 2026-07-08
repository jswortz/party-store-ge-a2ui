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

import json
import logging

from google.adk.events.event import Event
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

logger = logging.getLogger(__name__)


class A2uiRendererPlugin(BasePlugin):
    """A custom plugin that intercepts 'send_a2ui_json_to_client' tool responses

    and converts them to A2UI-compatible A2A parts, wrapping them in
    `<a2a_datapart_json>` wrappers so that the Gemini Enterprise client renders
    them.
    """

    def __init__(self, name: str = "a2ui_renderer"):
        super().__init__(name)

    async def on_event_callback(
        self, *, invocation_context, event: Event
    ) -> Event | None:
        logger.info("A2uiRendererPlugin: Intercepted event: %s", type(event))
        if event.content and event.content.parts:
            logger.info("A2uiRendererPlugin: Event content parts count: %d", len(event.content.parts))
            new_parts = []
            modified = False

            # Check if there is an A2UI response in the parts
            has_a2ui_response = any(
                part.function_response
                and part.function_response.name == "send_a2ui_json_to_client"
                for part in event.content.parts
            )
            if has_a2ui_response:
                logger.info("A2uiRendererPlugin: Found send_a2ui_json_to_client function response event!")

            for part in event.content.parts:
                if (
                    part.function_response
                    and part.function_response.name == "send_a2ui_json_to_client"
                ):
                    response = part.function_response.response or {}
                    a2ui_json_payload = response.get("validated_a2ui_json")
                    if a2ui_json_payload:
                        logger.info("A2uiRendererPlugin: Converting validated_a2ui_json payload to A2A tag...")
                        # Standardize all surfaceId properties to "canvas-surface" so the Gemini Enterprise panel renders them
                        if isinstance(a2ui_json_payload, list):
                            for cmd in a2ui_json_payload:
                                if isinstance(cmd, dict):
                                    if "beginRendering" in cmd and isinstance(cmd["beginRendering"], dict):
                                        cmd["beginRendering"]["surfaceId"] = "canvas-surface"
                                    if "surfaceUpdate" in cmd and isinstance(cmd["surfaceUpdate"], dict):
                                        cmd["surfaceUpdate"]["surfaceId"] = "canvas-surface"
                                    if "dataModelUpdate" in cmd and isinstance(cmd["dataModelUpdate"], dict):
                                        cmd["dataModelUpdate"]["surfaceId"] = "canvas-surface"

                        # Construct the A2A DataPart structure expected by the client
                        data_part = {
                            "kind": "data",
                            "metadata": {"mimeType": "application/json+a2ui"},
                            "data": a2ui_json_payload,
                        }

                        # Serialize and wrap in A2A tag
                        part_json = json.dumps(data_part, separators=(",", ":"))
                        wrapped_data = (
                            b"<a2a_datapart_json>"
                            + part_json.encode("utf-8")
                            + b"</a2a_datapart_json>"
                        )

                        # Create the new inline_data part
                        new_part = types.Part(
                            inline_data=types.Blob(
                                mime_type="text/plain", data=wrapped_data
                            )
                        )
                        new_parts.append(new_part)
                        modified = True
                        continue
                elif (
                    has_a2ui_response
                    and part.text
                    and "validated_a2ui_json" in part.text
                ):
                    logger.info("A2uiRendererPlugin: Dropping raw JSON text bubble from model response...")
                    # Skip the noise text part containing raw JSON
                    continue
                else:
                    new_parts.append(part)
            if modified:
                event.content.parts = new_parts
        return event
