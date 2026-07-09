import requests
import json
import time
from google.auth import default
from google.auth.transport.requests import Request

def main():
    creds, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    creds.refresh(Request())
    
    headers = {
        'Authorization': f'Bearer {creds.token}',
        'X-Goog-User-Project': 'wortz-project-352116',
        'Content-Type': 'application/json'
    }
    
    url_base = 'https://us-east1-aiplatform.googleapis.com/v1beta1/projects/679926387543/locations/us-east1/reasoningEngines/6620256267862540288/a2a/v1'
    
    # 1. Send message (A2A structure)
    payload = {
        'message': {
            'content': [
                {
                    'text': 'hello'
                }
            ]
        }
    }
    
    print("Sending message...")
    r = requests.post(f"{url_base}/message:send", headers=headers, json=payload)
    print(f"Status: {r.status_code}")
    res = r.json()
    print(json.dumps(res, indent=2))
    
    task_id = res.get('task', {}).get('id')
    if not task_id:
        print("No task ID returned!")
        return
        
    # Poll task status
    for i in range(25):
        print(f"\nPolling task status (Attempt {i+1})...")
        time.sleep(2)
        r = requests.get(f"{url_base}/tasks/{task_id}", headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code != 200:
             print(r.text)
             break
        task_res = r.json()
        state = task_res.get('status', {}).get('state')
        print(f"State: {state}")
        if state in ['TASK_STATE_COMPLETED', 'TASK_STATE_FAILED']:
             print(json.dumps(task_res, indent=2))
             break

if __name__ == "__main__":
    main()
