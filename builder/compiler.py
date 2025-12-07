import os
import subprocess
import tempfile

class Compiler:
    def __init__(self):
        self.builder_image = "tinygo/tinygo"

    def compile_in_docker(self, source_code, output_name="agent"):
        """
        Compiles Go code using a Dockerized TinyGo environment.
        """
        print("[*] Compiling with TinyGo (Dockerized)...")
        
        # Create a temp directory to mount
        with tempfile.TemporaryDirectory() as temp_dir:
            src_path = os.path.join(temp_dir, "main.go")
            bin_path = os.path.join(temp_dir, output_name)
            
            # Write source code
            with open(src_path, "w") as f:
                f.write(source_code)
                
            # Detect Architecture
            import platform
            machine = platform.machine().lower()
            goarch = "amd64"
            if "arm" in machine or "aarch64" in machine:
                goarch = "arm64"
            
            print(f"[*] Detected Host Arch: {machine} -> GOARCH={goarch}")

            # Docker run command
            # tinygo build -o /out/agent -target=linux -no-debug /src/main.go
            # We mount temp_dir to /app inside container
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{temp_dir}:/app",
                "-w", "/app",
                "-e", "CGO_ENABLED=0",
                "-e", "GOOS=linux",
                "-e", f"GOARCH={goarch}",
                self.builder_image,
                "tinygo", "build",
                "-o", output_name,
                "-no-debug",
                "-ldflags=-extldflags=-static", # Force pure static linking
                "main.go"
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                
                # Check if binary exists
                if not os.path.exists(bin_path):
                    raise Exception("Binary created but not found on host?")
                
                # UPX Compression - DISABLED due to SIGSEGV on ARM64/Alpine interactions
                # if self._is_tool_available("upx"):
                #     print("[*] Compressing with UPX...")
                #     subprocess.run(["upx", "--best", "--lzma", bin_path], check=True, capture_output=True)
                # else:
                #     print("[!] UPX not found on host, skipping compression.")

                # Read binary content to return it
                with open(bin_path, "rb") as f:
                    return f.read()

            except subprocess.CalledProcessError as e:
                print(f"[!] Compilation Failed: {e.stderr.decode()}")
                raise

    def _is_tool_available(self, name):
        from shutil import which
        return which(name) is not None
