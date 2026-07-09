import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.agent import app

async def main():
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="test_user", app_name="test")
    runner = Runner(agent=app.root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Show inventory status")]
    )

    print("--- Starting run ---")
    async for event in runner.run_async(
        new_message=message,
        user_id="test_user",
        session_id=session.id,
    ):
        print(f"Event author: {event.author}")
        if event.content:
            print("Parts:")
            for idx, part in enumerate(event.content.parts):
                print(f"  Part {idx}:")
                for attr in ['text', 'inline_data', 'function_call', 'function_response', 'file_data']:
                    val = getattr(part, attr, None)
                    if val is not None:
                        print(f"    {attr}: {type(val)} = {repr(val)[:200]}")
        print("-" * 20)
    print("--- Run completed ---")

if __name__ == "__main__":
    asyncio.run(main())
