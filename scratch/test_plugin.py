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

import asyncio
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import app

async def main():
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="test_user", app_name="test")
    
    # We pass the app.root_agent, and register the plugins from app.plugins to the runner.
    runner = Runner(
        agent=app.root_agent,
        session_service=session_service,
        app_name="test",
        plugins=app.plugins
    )

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Show inventory status")]
    )

    print("Running agent with user request 'Show inventory status'...")
    
    async for event in runner.run_async(
        new_message=message,
        user_id="test_user",
        session_id=session.id,
    ):
        author = event.author or "unknown"
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{author} text]: {part.text}")
                elif part.inline_data:
                    data_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type
                    # Print preview of the data bytes
                    preview = data_bytes[:100] if len(data_bytes) > 100 else data_bytes
                    print(f"[{author} inline_data ({mime_type})]: {preview}...")
                elif part.function_call:
                    print(f"[{author} function_call]: {part.function_call.name}")
                elif part.function_response:
                    print(f"[{author} function_response]: {part.function_response.name}")

    await runner.close()

if __name__ == "__main__":
    asyncio.run(main())
