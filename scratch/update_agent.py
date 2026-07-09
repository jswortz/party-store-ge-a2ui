import requests
import json
from google.auth import default
from google.auth.transport.requests import Request

def _get_bearer_token():
    credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    request = Request()
    credentials.refresh(request)
    return credentials.token

def update_agent():
    project_id = "wortz-project-352116"
    app_id = "gemini-enterprise-17634901_1763490144996"
    agent_id = "9406378961614108535"
    
    # 1. Get current agent
    url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/global/collections/default_collection/engines/{app_id}/"
        f"assistants/default_assistant/agents/{agent_id}"
    )

    headers = {
        "Authorization": f"Bearer {_get_bearer_token()}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }

    print("Fetching agent...")
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"Failed to fetch agent: {r.status_code}")
        print(r.text)
        return
        
    agent = r.json()
    a2a_def = agent.get("a2aAgentDefinition", {})
    card_str = a2a_def.get("jsonAgentCard")
    if not card_str:
        print("Agent card string not found.")
        return
        
    card = json.loads(card_str)
    old_url = card.get("url")
    new_url = "https://us-east1-aiplatform.googleapis.com/v1beta1/projects/679926387543/locations/us-east1/reasoningEngines/2552379904440139776/a2a"
    
    print(f"Old URL: {old_url}")
    print(f"New URL: {new_url}")
    
    card["url"] = new_url
    a2a_def["jsonAgentCard"] = json.dumps(card)
    
    patch_body = {
        "name": agent["name"],
        "a2aAgentDefinition": a2a_def
    }
    
    # 2. Patch agent
    patch_url = f"{url}?updateMask=a2aAgentDefinition.jsonAgentCard"
    print("Patching agent A2A definition...")
    r = requests.patch(patch_url, headers=headers, json=patch_body)
    print(f"Patch Status: {r.status_code}")
    if r.status_code == 200:
        print("Successfully updated agent A2A URL!")
        print(json.dumps(r.json(), indent=2))
    else:
        print(f"Failed to patch agent: {r.status_code}")
        print(r.text)

if __name__ == "__main__":
    update_agent()
