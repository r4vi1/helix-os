import os
import subprocess
import tempfile
import time

class Dockerizer:
    def __init__(self, registry_url="localhost:5001"):
        self.registry_url = registry_url

    def build_and_push(self, binary_data, image_name, metadata):
        """
        Builds a scratch image containing the binary and defined metadata, then pushes it.
        """
        print(f"[*] Building Docker image: {image_name}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save binary
            agent_path = os.path.join(temp_dir, "agent")
            with open(agent_path, "wb") as f:
                f.write(binary_data)
            os.chmod(agent_path, 0o755)
            
            # Create Dockerfile
            labels = " \\\n".join([f'"{k}"="{v}"' for k, v in metadata.items()])
            
            dockerfile_content = f"""
            FROM scratch
            COPY agent /agent
            LABEL {labels}
            ENTRYPOINT ["/agent"]
            """
            
            dockerfile_path = os.path.join(temp_dir, "Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write(dockerfile_content)
                
            # Build
            full_tag = f"{self.registry_url}/{image_name}:latest"
            
            try:
                subprocess.run(
                    ["docker", "build", "-t", full_tag, temp_dir],
                    check=True, capture_output=True
                )
                print(f"[*] Built {full_tag}")
                
                # Push
                print(f"[*] Pushing to {full_tag}...")
                subprocess.run(
                    ["docker", "push", full_tag],
                    check=True, capture_output=True
                )
                print("[*] Push success.")
                return full_tag
                
            except subprocess.CalledProcessError as e:
                print(f"[!] Docker Build/Push Failed: {e.stderr.decode()}")
                raise
