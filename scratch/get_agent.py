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

def get_agent():
    project_id = "wortz-project-352116"
    app_id = "gemini-enterprise-17634901_1763490144996"
    agent_id = "7101964700851895615"
    
    api_endpoint = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/global/collections/default_collection/engines/{app_id}/"
        f"assistants/default_assistant/agents/{agent_id}"
    )

    headers = {
        "Authorization": f"Bearer {_get_bearer_token()}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }

    response = requests.get(api_endpoint, headers=headers)
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Failed to query Discovery Engine API: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    get_agent()
