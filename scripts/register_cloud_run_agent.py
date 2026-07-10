"""Update the Gemini Enterprise agent registration to the deployed Cloud Run A2UI card.

The live GE agent already points at the Cloud Run /a2a/app endpoint, but its registered card
advertised preferredTransport=HTTP+JSON and lacked acceptsInlineCatalogs. This fetches the deployed
served card (JSONRPC + A2UI v0.8 extension with acceptsInlineCatalogs) and PATCHes the registration
so GE invokes the agent the way the server actually speaks it.
"""
import json
import requests
from google.auth import default
from google.auth.transport.requests import Request

PROJECT_ID = "wortz-project-352116"
APP_ID = "gemini-enterprise-17634901_1763490144996"
AGENT_ID = "10192074070999086566"
CARD_URL = "https://party-store-ge-a2ui-679926387543.us-east1.run.app/a2a/app/.well-known/agent-card.json"


def _token():
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def main():
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": PROJECT_ID,
    }

    print(f"Fetching deployed served card from {CARD_URL} ...")
    served = requests.get(CARD_URL, timeout=30)
    served.raise_for_status()
    card = served.json()
    # Ensure the card advertises the Cloud Run endpoint (it does via APP_URL) and JSONRPC.
    print(f"  url={card.get('url')} transport={card.get('preferredTransport')}")
    print(f"  extensions={[e.get('uri') for e in card.get('capabilities',{}).get('extensions',[])]}")

    base = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/"
        f"locations/global/collections/default_collection/engines/{APP_ID}/"
        f"assistants/default_assistant/agents/{AGENT_ID}"
    )

    print("Fetching current GE agent registration ...")
    cur = requests.get(base, headers=headers, timeout=30)
    cur.raise_for_status()
    agent = cur.json()

    a2a_def = agent.get("a2aAgentDefinition", {}) or {}
    a2a_def["jsonAgentCard"] = json.dumps(card)
    patch_body = {"name": agent["name"], "a2aAgentDefinition": a2a_def}

    patch_url = f"{base}?updateMask=a2aAgentDefinition.jsonAgentCard"
    print("Patching GE agent registration with the Cloud Run card ...")
    r = requests.patch(patch_url, headers=headers, json=patch_body, timeout=30)
    print(f"Patch status: {r.status_code}")
    if r.status_code == 200:
        print("✓ GE agent updated to the deployed Cloud Run A2UI card.")
    else:
        print(r.text)
        r.raise_for_status()


if __name__ == "__main__":
    main()
