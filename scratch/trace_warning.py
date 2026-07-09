import logging
import vertexai
import sys

def my_warning(msg, *args, **kwargs):
    # Print the stack trace leading to the warning
    import traceback
    print("=== WARNING DETECTED ===")
    traceback.print_stack()
    print("========================")
    original_warning(msg, *args, **kwargs)

# Hook the warning method
original_warning = logging.warning
logging.warning = my_warning

# Also hook root logger warning
logging.root.warning = my_warning

def main():
    vertexai.init(project="wortz-project-352116", location="us-east1")
    from vertexai.preview.reasoning_engines import ReasoningEngine
    
    engine_id = "projects/679926387543/locations/us-east1/reasoningEngines/8056904548993728512"
    re = ReasoningEngine(engine_id)

if __name__ == "__main__":
    main()
