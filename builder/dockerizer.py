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
FROM gcr.io/distroless/static:nonroot
WORKDIR /
COPY agent /agent
LABEL helix.task="{metadata['task']}"
LABEL helix.capabilities="{metadata['capabilities']}"
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

    def verify_image(self, image_tag):
        """
        Verifies that the image can run and is valid (not segfaulting immediately).
        Returns True if successful, raises Exception if not.
        """
        print(f"[*] Verifying image {image_tag}...")
        try:
            # We run it with a dummy argument to see if it starts up and handles args.
            # We expect a success (0) or a handled error (maybe 1), but not 139 (SEGV).
            cmd = ["docker", "run", "--rm", image_tag, "verify_startup"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 139:
                raise Exception(f"SIGSEGV (139) detected during verification of {image_tag}")
            if result.returncode == 126 or result.returncode == 127:
                raise Exception(f"Command execution error ({result.returncode}) - possibly arch mismatch")
                
            print(f"[*] Verification Passed (Exit Code: {result.returncode})")
            return True
        except Exception as e:
            print(f"[!] Verification Failed: {e}")
            raise
