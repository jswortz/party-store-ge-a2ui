import asyncio
import json
import httpx
from app.fast_api_app import app

async def main():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        # Clean up old session
        await client.delete("/apps/app/users/test_user/sessions/test_session")
        
        # Create new session
        session_payload = {
            "session_id": "test_session"
        }
        create_resp = await client.post("/apps/app/users/test_user/sessions", json=session_payload)
        print("Session Create Status:", create_resp.status_code)
        
        # Turn 1: Show inventory
        payload1 = {
            "app_name": "app",
            "user_id": "test_user",
            "session_id": "test_session",
            "new_message": {
                "parts": [
                    {"text": "Show me the inventory status"}
                ]
            }
        }
        resp1 = await client.post("/run", json=payload1)
        print("Turn 1 Status Code:", resp1.status_code)
        print("Turn 1 Raw Response:")
        print(resp1.text)

if __name__ == "__main__":
    asyncio.run(main())
