import asyncio
import json
import httpx
from app.fast_api_app import app

async def run_conversation():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        # Clean up old session
        await client.delete("/apps/app/users/test_user/sessions/test_session")
        
        # Create new session
        session_payload = {
            "session_id": "test_session"
        }
        create_resp = await client.post("/apps/app/users/test_user/sessions", json=session_payload)
        print("Session Create Status:", create_resp.status_code)
        if create_resp.status_code >= 400:
            print("Session Create Error:", create_resp.text)
            return

        # Turn 1: Show inventory
        print("\n--- Turn 1: Show Inventory ---")
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
        try:
            events = resp1.json()
            print("Turn 1 response snippets:")
            for event in events:
                if event.get("content"):
                    for part in event["content"].get("parts", []):
                        if "text" in part:
                            print("  [Agent text]:", part["text"][:200] + "..." if len(part["text"]) > 200 else part["text"])
                        if "functionCall" in part:
                            fn_call = part["functionCall"]
                            print(f"  [Function Call]: {fn_call['name']}({fn_call.get('args')})")
        except Exception as e:
            print("Error parsing Turn 1:", e)

        # Turn 2: Forecast
        print("\n--- Turn 2: Forecast for halloween_skeleton ---")
        payload2 = {
            "app_name": "app",
            "user_id": "test_user",
            "session_id": "test_session",
            "new_message": {
                "parts": [
                    {"text": "Show me the sales forecast for halloween_skeleton"}
                ]
            }
        }
        resp2 = await client.post("/run", json=payload2)
        print("Turn 2 Status Code:", resp2.status_code)
        try:
            events = resp2.json()
            for event in events:
                if event.get("content"):
                    for part in event["content"].get("parts", []):
                        if "text" in part:
                            print("  [Agent text]:", part["text"][:200] + "..." if len(part["text"]) > 200 else part["text"])
                        if "functionCall" in part:
                            fn_call = part["functionCall"]
                            print(f"  [Function Call]: {fn_call['name']}({fn_call.get('args')})")
        except Exception as e:
            print("Error parsing Turn 2:", e)

        # Turn 3: Order
        print("\n--- Turn 3: Order 300 halloween_skeletons ---")
        payload3 = {
            "app_name": "app",
            "user_id": "test_user",
            "session_id": "test_session",
            "new_message": {
                "parts": [
                    {"text": "We need to order 300 halloween_skeletons. Please place the order."}
                ]
            }
        }
        resp3 = await client.post("/run", json=payload3)
        print("Turn 3 Status Code:", resp3.status_code)
        try:
            events = resp3.json()
            with open("scratch/turn3_events.json", "w") as f:
                json.dump(events, f, indent=2)
            print("Turn 3 events dumped to scratch/turn3_events.json")
            for event in events:
                if event.get("content"):
                    for part in event["content"].get("parts", []):
                        if "text" in part:
                            print("  [Agent text]:", part["text"][:200] + "..." if len(part["text"]) > 200 else part["text"])
                        if "functionCall" in part:
                            fn_call = part["functionCall"]
                            print(f"  [Function Call]: {fn_call['name']}({fn_call.get('args')})")
        except Exception as e:
            print("Error parsing Turn 3:", e)

if __name__ == "__main__":
    asyncio.run(run_conversation())
