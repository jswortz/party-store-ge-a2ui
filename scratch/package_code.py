import os
import tarfile
import base64
import io

def package_code():
    print("Packaging source code...")
    cwd = os.getcwd()
    
    # Create in-memory tar.gz
    tar_io = io.BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w:gz") as tar:
        # Add app/ directory
        tar.add("app", arcname="app")
        # Add requirements file if it exists
        if os.path.exists("requirements.txt"):
            tar.add("requirements.txt", arcname="requirements.txt")
            
    tar_io.seek(0)
    encoded = base64.b64encode(tar_io.read()).decode("utf-8")
    
    # Write to dummy_source.b64
    target_path = "deployment/terraform/shared/dummy_source.b64"
    print(f"Writing base64 source to {target_path}...")
    with open(target_path, "w") as f:
        f.write(encoded)
        
    print("Done packaging!")

if __name__ == "__main__":
    package_code()
