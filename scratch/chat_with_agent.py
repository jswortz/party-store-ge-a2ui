import os
import requests
import json
from google.auth import default
from google.auth.transport.requests import Request

def _get_bearer_token():
    credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    request = Request()
    credentials.refresh(request)
    return credentials.token

def chat_with_agent():
    project_id = "wortz-project-352116"
    app_id = "gemini-enterprise-17634901_1763490144996"
    agent_id = "9406378961614108535"  # Our registered A2A agent ID
    
    # Discovery Engine StreamAssist API for the specific Agent
    api_endpoint = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/global/collections/default_collection/engines/{app_id}/"
        f"assistants/default_assistant/agents/{agent_id}:streamAssist"
    )

    headers = {
        "Authorization": f"Bearer {_get_bearer_token()}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }

    # StreamAssist payload
    payload = {
        "inputText": "Show inventory status"
    }
    
    print(f"Calling StreamAssist on agent {agent_id} at {api_endpoint}...")
    response = requests.post(api_endpoint, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    try:
        # Since it streams back SSE/NDJSON, we can print the text response or iterate
        print(response.text)
    except Exception as e:
        print(f"Failed to read response: {e}")

if __name__ == "__main__":
    chat_with_agent()
