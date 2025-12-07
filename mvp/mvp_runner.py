import time
import subprocess
try:
    from config import MODEL_NAME, HELIX_SUB_AGENT_PROVIDER, GEMINI_API_KEY
    from mvp_whisper import transcribe_audio
    from mvp_router import route_intent
except ImportError:
    from .config import MODEL_NAME, HELIX_SUB_AGENT_PROVIDER, GEMINI_API_KEY
    from .mvp_whisper import transcribe_audio
    from .mvp_router import route_intent

def execute_sub_agent(task_spec):
    """
    Spawns a transient Docker container to execute the task.
    """
    print(f"[*] Spawning Sub-Agent for task: {task_spec[:50]}...")

    # Build the command arguments
    cmd = [
        "docker", "run", "--rm", 
        "helix-agent-go", 
        "--task", task_spec,
        "--provider", HELIX_SUB_AGENT_PROVIDER
    ]

    # Handle Provider-specific args
    if HELIX_SUB_AGENT_PROVIDER == "cloud":
        if not GEMINI_API_KEY:
            print("[!] Error: HELIX_SUB_AGENT_PROVIDER is 'cloud' but GEMINI_API_KEY is not set.")
            return
        # Pass API key securely via env var
        cmd.extend(["-e", f"GEMINI_API_KEY={GEMINI_API_KEY}"])
    else:
        # Local Ollama Provider
        cmd.extend(["--model", MODEL_NAME])

    try:
        # Run the container
        # Note: --network host for Linux, host.docker.internal for Mac inside container logic
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"[*] Sub-Agent Finished. Output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"[!] Sub-Agent Failed: {e.stderr}")
    except FileNotFoundError:
        print("[!] Docker not found. Is it installed and in your PATH?")

def execute_action(intent):
    """
    Executes the action determined by the router.
    """
    print(f"[*] Executing Action: {intent.get('action', 'unknown')}")
    
    action = intent.get("action", "unknown")
    if action == 'get_weather':
        print(f"    -> Fetching weather for {intent['params']['location']}...")
        # Stub: Call weather API
        print("    -> It is 22°C and Sunny.")
    elif action == 'save_reminder':
        print(f"    -> Saving reminder: {intent['params']['content']}")
        # Stub: Save to DB
        print("    -> Reminder saved.")
    elif intent['action'] == "spawn_agent":
        task_spec = intent.get("params", {}).get("task_spec", "")
        if task_spec:
            execute_sub_agent(task_spec)
        else:
            print("[!] Error: No task_spec provided for sub_agent.")
    else:
        print("    -> Unknown command, logging.")

def check_docker():
    """
    Verifies that any container runtime (Docker/OrbStack) is running.
    """
    try:
        subprocess.run(["docker", "version"], check=True, capture_output=True)
        print("[*] Container Runtime detected.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[!] Error: Docker/OrbStack is not running or not in PATH.")
        print("    Please start Docker Desktop or OrbStack.")
        exit(1)

def main():
    print(f"=== HelixOS MVP Running ({MODEL_NAME}) ===")
    check_docker()
    
    # Initialize Whisper
    print("[*] Loading Whisper model 'base'...")
    try:
        while True:
            # 1. Input
            text = transcribe_audio()
            print(f"[*] Heard: {text}")
            
            # 2. Route
            intent = route_intent(text)
            
            # 3. Execute
            execute_action(intent)
            
            print("-" * 30)
            # Break for demo purposes so it doesn't loop infinitely in a non-interactive way
            # In real life, this would wait for a wake word or button press
            user_input = input("Press Enter to listen again, or 'q' to quit: ")
            if user_input.lower() == 'q':
                break
                
    except KeyboardInterrupt:
        print("\nStopping HelixOS...")

if __name__ == "__main__":
    main()
