import os

def detect_jetski():
    ide_port = os.environ.get("GEMINI_CLI_IDE_SERVER_PORT")
    ssh_sock = os.environ.get("SSH_AUTH_SOCK", "")
    
    is_jetski_ide = ide_port is not None or ".jetski-server" in ssh_sock
    
    print("=== Jetski IDE Detection ===")
    print(f"GEMINI_CLI_IDE_SERVER_PORT: {ide_port}")
    print(f"SSH_AUTH_SOCK: {ssh_sock}")
    print(f"Detected Jetski IDE Environment: {is_jetski_ide}")

if __name__ == "__main__":
    detect_jetski()
