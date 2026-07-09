import json
import traceback

def main():
    try:
        with open("scratch/turn2_events.json", "r") as f:
            events = json.load(f)
            
        tool_payload = None
        sent_payload = None
        
        for idx, event in enumerate(events):
            content = event.get("content", {})
            parts = content.get("parts", [])
            for part_idx, part in enumerate(parts):
                fn_resp = part.get("functionResponse", {})
                if fn_resp.get("name") == "get_sales_forecast":
                    response = fn_resp.get("response", {})
                    tool_payload = response.get("a2ui_payload_str")
                    print(f"Found tool response for get_sales_forecast. Length: {len(tool_payload) if tool_payload else 'None'}")
                    
                fn_call = part.get("functionCall", {})
                if fn_call.get("name") == "send_a2ui_json_to_client":
                    sent_payload = fn_call.get("args", {}).get("a2ui_json")
                    print(f"Found send_a2ui_json_to_client call. Length: {len(sent_payload) if sent_payload else 'None'}")
        
        if tool_payload:
            try:
                json.loads(tool_payload)
                print("Tool payload is VALID JSON.")
            except Exception as e:
                print(f"Tool payload is INVALID JSON: {e}")
                
        if sent_payload:
            try:
                json.loads(sent_payload)
                print("Sent payload is VALID JSON.")
            except Exception as e:
                print(f"Sent payload is INVALID JSON: {e}")
                
        if tool_payload and sent_payload:
            if tool_payload == sent_payload:
                print("Tool payload and Sent payload are EXACTLY IDENTICAL.")
            else:
                print("Tool payload and Sent payload are DIFFERENT!")
                # Print where they differ
                min_len = min(len(tool_payload), len(sent_payload))
                for i in range(min_len):
                    if tool_payload[i] != sent_payload[i]:
                        print(f"Differ at index {i}:")
                        print(f"Tool: {tool_payload[i-20:i]} >>> {tool_payload[i]} <<< {tool_payload[i+1:i+20]}")
                        print(f"Sent: {sent_payload[i-20:i]} >>> {sent_payload[i]} <<< {sent_payload[i+1:i+20]}")
                        break
                if len(tool_payload) != len(sent_payload):
                    print(f"Lengths differ. Tool: {len(tool_payload)}, Sent: {len(sent_payload)}")
                    
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    main()
