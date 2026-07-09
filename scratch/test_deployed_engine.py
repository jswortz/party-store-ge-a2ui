import os
import vertexai
from vertexai.preview.reasoning_engines import ReasoningEngine

def test_deployed():
    vertexai.init(project="wortz-project-352116", location="us-east1")
    
    engine_id = "projects/679926387543/locations/us-east1/reasoningEngines/8056904548993728512"
    print(f"Loading reasoning engine: {engine_id}...")
    try:
        remote_agent = ReasoningEngine(engine_id)
        print("✓ Loaded reasoning engine successfully.")
        
        print("Sending query 'Hi' to remote agent...")
        response = remote_agent.query(text="Hi")
        print(f"✓ Query response: {response}")
    except Exception as e:
        print(f"✗ Query failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_deployed()
