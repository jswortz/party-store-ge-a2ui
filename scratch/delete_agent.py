import sys
import requests
from google.auth import default
from google.auth.transport.requests import Request

def _get_bearer_token():
    credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    request = Request()
    credentials.refresh(request)
    return credentials.token

def delete_agent(agent_name):
    project_id = "wortz-project-352116"
    headers = {
        "Authorization": f"Bearer {_get_bearer_token()}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }

    print(f"Deleting agent: {agent_name}...")
    api_endpoint = f"https://discoveryengine.googleapis.com/v1alpha/{agent_name}"
    response = requests.delete(api_endpoint, headers=headers)
    if response.status_code == 200 or response.status_code == 204:
        print("Successfully deleted!")
    else:
        print(f"Failed to delete: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_agent.py <agent_resource_name>")
        sys.exit(1)
    delete_agent(sys.argv[1])
