"""
WASM Builder
=============
Compiles Go code to WebAssembly (WASI target) and stores in registry.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List

from .wasm_registry import WASMRegistry, WASMManifest


class WASMBuilder:
    """
    Builds Go code into WASM modules for browser execution.
    
    Uses GOOS=wasip1 GOARCH=wasm for WASI-compatible output.
    """
    
    def __init__(self, registry: WASMRegistry = None):
        self.registry = registry or WASMRegistry()
    
    def compile(self, source_code: str, output_name: str = "agent.wasm") -> bytes:
        """
        Compile Go source code to WASM binary.
        
        Args:
            source_code: Go source code as string
            output_name: Name of output file (default: agent.wasm)
        
        Returns:
            Compiled WASM binary as bytes
        """
        print("[*] Compiling Go to WASM (WASI target)...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            src_path = temp_path / "main.go"
            wasm_path = temp_path / output_name
            
            # Write source code
            src_path.write_text(source_code)
            
            # Compile using Docker for consistency
            # Using golang:alpine with WASI target
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{temp_dir}:/app",
                "-w", "/app",
                "-e", "GOOS=wasip1",
                "-e", "GOARCH=wasm",
                "-e", "CGO_ENABLED=0",
                "golang:1.22-alpine",
                "go", "build",
                "-ldflags=-s -w",
                "-o", output_name,
                "main.go"
            ]
            
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                print("[*] WASM compilation successful")
            except subprocess.CalledProcessError as e:
                print(f"[!] WASM Compilation Failed: {e.stderr}")
                raise Exception(f"WASM compilation failed: {e.stderr}")
            
            # Read and return the WASM binary
            if not wasm_path.exists():
                raise Exception("WASM binary not found after compilation")
            
            wasm_binary = wasm_path.read_bytes()
            print(f"[*] WASM binary size: {len(wasm_binary)} bytes")
            return wasm_binary
    
    def compile_native(self, source_code: str, output_name: str = "agent.wasm") -> bytes:
        """
        Compile Go source code to WASM using native Go (if available).
        Fallback for systems without Docker.
        
        Requires Go 1.21+ installed locally.
        """
        print("[*] Compiling Go to WASM (native, WASI target)...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            src_path = temp_path / "main.go"
            wasm_path = temp_path / output_name
            
            # Write source code
            src_path.write_text(source_code)
            
            # Set environment for WASM compilation
            env = os.environ.copy()
            env["GOOS"] = "wasip1"
            env["GOARCH"] = "wasm"
            env["CGO_ENABLED"] = "0"
            
            cmd = [
                "go", "build",
                "-ldflags=-s -w",
                "-o", str(wasm_path),
                str(src_path)
            ]
            
            try:
                result = subprocess.run(
                    cmd, 
                    check=True, 
                    capture_output=True, 
                    text=True,
                    env=env,
                    cwd=temp_dir
                )
                print("[*] WASM compilation successful (native)")
            except subprocess.CalledProcessError as e:
                print(f"[!] WASM Compilation Failed: {e.stderr}")
                raise Exception(f"WASM compilation failed: {e.stderr}")
            except FileNotFoundError:
                raise Exception("Go compiler not found. Install Go 1.21+ or use Docker compilation.")
            
            # Read and return the WASM binary
            if not wasm_path.exists():
                raise Exception("WASM binary not found after compilation")
            
            wasm_binary = wasm_path.read_bytes()
            print(f"[*] WASM binary size: {len(wasm_binary)} bytes")
            return wasm_binary
    
    def build_and_register(
        self, 
        source_code: str, 
        agent_name: str,
        task_description: str,
        capabilities: List[str] = None,
        use_docker: bool = True
    ) -> str:
        """
        Compile Go code to WASM and register in the WASM registry.
        
        Args:
            source_code: Go source code
            agent_name: Name for the agent (used as directory name)
            task_description: Description of what the agent does (for search)
            capabilities: List of capabilities (e.g., ["compute", "math"])
            use_docker: Whether to use Docker for compilation
        
        Returns:
            Path to the stored WASM file
        """
        print(f"[*] Building WASM agent: {agent_name}")
        
        # Compile
        if use_docker:
            wasm_binary = self.compile(source_code)
        else:
            wasm_binary = self.compile_native(source_code)
        
        # Create manifest
        manifest = WASMManifest(
            name=agent_name,
            task=task_description,
            runtime="wasm",
            capabilities=capabilities or [],
            created=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        
        # Store in registry
        wasm_path = self.registry.store(agent_name, wasm_binary, manifest)
        
        print(f"[*] WASM agent registered: {agent_name}")
        return wasm_path
    
    def verify(self, agent_name: str) -> bool:
        """
        Verify that a WASM module is valid.
        Basic validation - checks file exists and has WASM magic bytes.
        """
        wasm_binary = self.registry.get_wasm_binary(agent_name)
        if not wasm_binary:
            print(f"[!] WASM agent not found: {agent_name}")
            return False
        
        # Check WASM magic bytes: \0asm
        if len(wasm_binary) < 4:
            print(f"[!] WASM binary too small: {len(wasm_binary)} bytes")
            return False
        
        magic = wasm_binary[:4]
        expected_magic = b'\x00asm'
        
        if magic != expected_magic:
            print(f"[!] Invalid WASM magic bytes: {magic.hex()}")
            return False
        
        print(f"[*] WASM verification passed: {agent_name}")
        return True


def is_wasm_suitable(task_description: str, required_apis: List[str]) -> bool:
    """
    Determine if a task can run as WASM in the browser.
    
    WASM is suitable when:
    - Pure computation (no external API calls)
    - No secrets/credentials required
    - No persistent storage needed
    
    Args:
        task_description: The task to evaluate
        required_apis: List of API keys the task needs
    
    Returns:
        True if task can run as WASM, False if it needs K8s
    """
    # If any APIs are required, use K8s (browser can't hold secrets safely)
    if required_apis:
        return False
    
    task_lower = task_description.lower()
    
    # Keywords that indicate WASM-incompatible tasks
    k8s_required_keywords = [
        "api", "http", "fetch", "request", "download",
        "secret", "key", "credential", "auth", "token",
        "database", "storage", "persist", "save", "file",
        "docker", "container", "deploy"
    ]
    
    for keyword in k8s_required_keywords:
        if keyword in task_lower:
            return False
    
    # Keywords that indicate WASM-suitable tasks
    wasm_suitable_keywords = [
        "calculate", "compute", "math", "fibonacci", "prime",
        "factorial", "sum", "multiply", "divide", "add",
        "parse", "transform", "format", "convert", "encode", "decode",
        "sort", "filter", "process", "analyze"
    ]
    
    for keyword in wasm_suitable_keywords:
        if keyword in task_lower:
            return True
    
    # Default: prefer K8s for safety (more capable)
    return False
