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

def list_agents():
    project_id = "wortz-project-352116"
    app_id = "gemini-enterprise-17634901_1763490144996"
    
    api_endpoint = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/global/collections/default_collection/engines/{app_id}/"
        "assistants/default_assistant/agents"
    )

    headers = {
        "Authorization": f"Bearer {_get_bearer_token()}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }

    response = requests.get(api_endpoint, headers=headers)
    if response.status_code == 200:
        agents = response.json().get("agents", [])
        for agent in agents:
            display_name = agent.get('displayName', '').lower()
            name = agent.get('name', '').lower()
            if "party" in display_name or "a2ui" in display_name or "party" in name or "a2ui" in name:
                print("-" * 60)
                print(f"Name: {agent.get('name')}")
                print(f"DisplayName: {agent.get('displayName')}")
                print(f"Description: {agent.get('description')}")
                print("A2A Definition:")
                print(json.dumps(agent.get("a2aAgentDefinition"), indent=2))
    else:
        print(f"Failed to query Discovery Engine API: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    list_agents()
