import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.agent import app
from app.a2ui_config import catalog
from a2ui.adk.a2a.part_converter import A2uiPartConverter

async def main():
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="test_user", app_name="test")
    
    # Run WITHOUT plugins
    runner = Runner(agent=app.root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Show inventory status")]
    )

    converter = A2uiPartConverter(a2ui_catalog=catalog)

    print("--- Starting run ---")
    async for event in runner.run_async(
        new_message=message,
        user_id="test_user",
        session_id=session.id,
    ):
        print(f"\nEvent author: {event.author}")
        if event.content:
            for idx, part in enumerate(event.content.parts):
                print(f"  Part {idx} (original):")
                for attr in ['text', 'inline_data', 'function_call', 'function_response']:
                    val = getattr(part, attr, None)
                    if val is not None:
                        print(f"    {attr}: {type(val)}")
                
                # Run the part through A2uiPartConverter
                try:
                    a2a_parts = converter.convert(part)
                    print(f"  -> Converted to {len(a2a_parts)} A2A parts:")
                    for a2a_part in a2a_parts:
                        print(f"    Type: {type(a2a_part.root)}")
                        print(f"    Data: {repr(getattr(a2a_part.root, 'data', None))[:150]}")
                        print(f"    Metadata: {getattr(a2a_part.root, 'metadata', None)}")
                except Exception as e:
                    print(f"  -> Conversion FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
