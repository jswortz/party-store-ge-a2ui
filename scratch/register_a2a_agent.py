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

def register_or_update_agent():
    project_id = "wortz-project-352116"
    app_id = "gemini-enterprise-17634901_1763490144996"
    agent_id = "11231632177925702454"
    runtime_id = "765629528839028736"
    
    # 1. Fetch the A2A card from the deployed reasoning engine
    card_url = f"https://us-east1-aiplatform.googleapis.com/v1beta1/projects/679926387543/locations/us-east1/reasoningEngines/{runtime_id}/a2a/v1/card"
    headers = {
        "Authorization": f"Bearer {_get_bearer_token()}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }
    
    print(f"Fetching card from {card_url}...")
    response = requests.get(card_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch agent card: {response.status_code}")
        print(response.text)
        return
        
    card_json = response.json()
    
    # 2. Correct the A2A URL to point to us-east1 instead of us-central1
    card_json["url"] = f"https://us-east1-aiplatform.googleapis.com/v1beta1/projects/679926387543/locations/us-east1/reasoningEngines/{runtime_id}/a2a"
    
    # Serialize back to string
    card_str = json.dumps(card_json)
    print("✓ Agent card fetched and URL corrected successfully.")
    
    # 3. Delete the old agent registration first
    api_endpoint = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/global/collections/default_collection/engines/{app_id}/"
        f"assistants/default_assistant/agents/{agent_id}"
    )
    
    print(f"Deleting old agent registration at {api_endpoint}...")
    delete_response = requests.delete(api_endpoint, headers=headers)
    if delete_response.status_code in [200, 204]:
        print("✓ Old agent registration deleted successfully.")
    elif delete_response.status_code == 404:
        print("Agent registration not found (already deleted).")
    else:
        print(f"Failed to delete old agent: {delete_response.status_code}")
        print(delete_response.text)
        return
        
    # 4. Perform a POST request to register the new A2A agent
    create_endpoint = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/global/collections/default_collection/engines/{app_id}/"
        "assistants/default_assistant/agents"
    )
    
    payload = {
        "displayName": "Party Store Supply Chain Agent",
        "description": "A2A Supply Chain Agent with A2UI capability.",
        "a2aAgentDefinition": {
            "jsonAgentCard": card_str
        }
    }
    
    print(f"Creating new A2A agent registration at {create_endpoint}...")
    create_response = requests.post(create_endpoint, headers=headers, json=payload)
    if create_response.status_code in [200, 201]:
        print("✓ Agent successfully registered as A2A in Gemini Enterprise!")
        print(json.dumps(create_response.json(), indent=2))
    else:
        print(f"Failed to register A2A agent: {create_response.status_code}")
        print(create_response.text)

if __name__ == "__main__":
    register_or_update_agent()
