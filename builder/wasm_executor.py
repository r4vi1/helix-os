"""
WASM Executor
=============
Execute WASM tasks via NATS messaging to browser worker pool.
"""

import json
import time
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class WASMTaskResult:
    """Result from a WASM task execution."""
    success: bool
    output: Any  # JSON output from the WASM module
    error: Optional[str] = None
    execution_time_ms: float = 0
    worker_id: Optional[str] = None


class WASMExecutor:
    """
    Execute WASM modules via NATS messaging to browser workers.
    
    Flow:
    1. Publish task to helix.tasks.wasm
    2. Browser workers (in queue group) receive task
    3. Worker executes WASM, publishes result
    4. Executor awaits response with timeout
    """
    
    DEFAULT_TIMEOUT = 30.0  # seconds
    TASK_SUBJECT = "helix.tasks.wasm"
    
    def __init__(self, nats_url: str = "nats://localhost:4222"):
        self.nats_url = nats_url
        self._nc = None  # NATS connection (lazy init)
    
    async def connect(self):
        """Connect to NATS server."""
        try:
            import nats
            self._nc = await nats.connect(self.nats_url)
            print(f"[*] Connected to NATS at {self.nats_url}")
        except ImportError:
            raise ImportError("nats-py not installed. Run: pip install nats-py")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to NATS: {e}")
    
    async def disconnect(self):
        """Disconnect from NATS."""
        if self._nc:
            await self._nc.close()
            self._nc = None
    
    async def execute(
        self,
        wasm_path: str,
        input_data: str,
        timeout: float = None
    ) -> WASMTaskResult:
        """
        Execute a WASM module via browser worker pool.
        
        Args:
            wasm_path: Path or URL to WASM module
            input_data: Input argument to pass to WASM module
            timeout: Max seconds to wait for result
        
        Returns:
            WASMTaskResult with output or error
        """
        if not self._nc:
            await self.connect()
        
        timeout = timeout or self.DEFAULT_TIMEOUT
        task_id = str(uuid.uuid4())[:8]
        
        # Create task message
        task_message = {
            "task_id": task_id,
            "wasm_path": wasm_path,
            "input": input_data,
            "timestamp": time.time()
        }
        
        print(f"[*] Dispatching WASM task {task_id}: {wasm_path}")
        start_time = time.time()
        
        try:
            # Use NATS request/reply pattern
            response = await self._nc.request(
                self.TASK_SUBJECT,
                json.dumps(task_message).encode(),
                timeout=timeout
            )
            
            execution_time = (time.time() - start_time) * 1000  # ms
            result_data = json.loads(response.data.decode())
            
            if result_data.get("error"):
                return WASMTaskResult(
                    success=False,
                    output=None,
                    error=result_data["error"],
                    execution_time_ms=execution_time,
                    worker_id=result_data.get("worker_id")
                )
            
            return WASMTaskResult(
                success=True,
                output=result_data.get("output"),
                execution_time_ms=execution_time,
                worker_id=result_data.get("worker_id")
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            if "timeout" in error_msg.lower():
                error_msg = f"WASM execution timed out after {timeout}s (no browser workers available?)"
            
            return WASMTaskResult(
                success=False,
                output=None,
                error=error_msg,
                execution_time_ms=execution_time
            )
    
    def execute_sync(
        self,
        wasm_path: str,
        input_data: str,
        timeout: float = None
    ) -> WASMTaskResult:
        """
        Synchronous wrapper for execute().
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.execute(wasm_path, input_data, timeout)
        )
    
    async def check_workers(self) -> Dict[str, Any]:
        """
        Check if any browser workers are connected.
        Sends a ping to the worker pool.
        """
        if not self._nc:
            await self.connect()
        
        ping_message = {
            "type": "ping",
            "timestamp": time.time()
        }
        
        try:
            response = await self._nc.request(
                f"{self.TASK_SUBJECT}.ping",
                json.dumps(ping_message).encode(),
                timeout=5.0
            )
            
            result = json.loads(response.data.decode())
            return {
                "available": True,
                "workers": result.get("workers", 1),
                "latency_ms": (time.time() - ping_message["timestamp"]) * 1000
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }


class LocalWASMExecutor:
    """
    Execute WASM modules locally using wasmtime.
    Fallback when no browser workers are available.
    """
    
    def __init__(self):
        self._wasmtime_available = None
    
    def _check_wasmtime(self) -> bool:
        """Check if wasmtime is available."""
        if self._wasmtime_available is not None:
            return self._wasmtime_available
        
        try:
            import subprocess
            result = subprocess.run(
                ["wasmtime", "--version"],
                capture_output=True,
                text=True
            )
            self._wasmtime_available = result.returncode == 0
        except FileNotFoundError:
            self._wasmtime_available = False
        
        return self._wasmtime_available
    
    def execute(
        self,
        wasm_path: str,
        input_data: str,
        timeout: float = 30.0
    ) -> WASMTaskResult:
        """
        Execute WASM module locally using wasmtime CLI.
        
        Args:
            wasm_path: Path to WASM module
            input_data: Input argument to pass
            timeout: Max seconds to wait
        
        Returns:
            WASMTaskResult with output or error
        """
        if not self._check_wasmtime():
            return WASMTaskResult(
                success=False,
                output=None,
                error="wasmtime not installed. Run: brew install wasmtime"
            )
        
        import subprocess
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["wasmtime", wasm_path, "--", input_data],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            if result.returncode != 0:
                return WASMTaskResult(
                    success=False,
                    output=None,
                    error=result.stderr or f"Exit code: {result.returncode}",
                    execution_time_ms=execution_time,
                    worker_id="local"
                )
            
            # Try to parse as JSON
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                output = result.stdout
            
            return WASMTaskResult(
                success=True,
                output=output,
                execution_time_ms=execution_time,
                worker_id="local"
            )
            
        except subprocess.TimeoutExpired:
            return WASMTaskResult(
                success=False,
                output=None,
                error=f"Execution timed out after {timeout}s",
                execution_time_ms=timeout * 1000,
                worker_id="local"
            )
        except Exception as e:
            return WASMTaskResult(
                success=False,
                output=None,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
                worker_id="local"
            )
