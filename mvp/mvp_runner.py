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

def handle_complex_task(task_spec):
    """
    Uses the Agent Builder ecosystem (Search -> Build -> Run) to solve a task.
    """
    print(f"[*] Handling Complex Task: {task_spec[:50]}...")
    
    # Lazy import to avoid circular dependency issues at top level if any
    try:
        from builder.search_tool import AgentSearchTool
        from builder.controller import SubAgentController
    except ImportError:
        # Fallback for when running from mvp/ dir directly without correct path
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from builder.search_tool import AgentSearchTool
        from builder.controller import SubAgentController

    search_tool = AgentSearchTool()
    
    # 1. Search Logic
    print(f"    -> [SEARCH] Looking for existing agent...")
    agent_image = search_tool.search(task_spec)
    
    if agent_image:
        print(f"    -> [FOUND] Using cached agent: {agent_image}")
    else:
        print(f"    -> [MISS] No suitable agent found. Initiating Build Process.")
        # 2. Build Logic
        controller = SubAgentController()
        try:
            agent_image = controller.create_agent(task_spec)
            print(f"    -> [BUILT] New agent ready: {agent_image}")
        except Exception as e:
            print(f"    [!] Build Failed: {e}")
            return

    # 3. Execution Logic
    if agent_image:
        print(f"    -> [EXEC] Running {agent_image}...")
        try:
            # Import config to get API keys
            from mvp.config import GEMINI_API_KEY, GOOGLE_SEARCH_API_KEY
            
            # Build docker run command with API keys
            cmd = ["docker", "run", "--rm"]
            
            if GEMINI_API_KEY:
                cmd.extend(["-e", f"GEMINI_API_KEY={GEMINI_API_KEY}"])
            if GOOGLE_SEARCH_API_KEY:
                cmd.extend(["-e", f"GOOGLE_SEARCH_API_KEY={GOOGLE_SEARCH_API_KEY}"])
                
            cmd.append(agent_image)
            
            # Pass the task specification as the first argument to the agent
            cmd.append(task_spec)

            # Run without check=True to handle non-zero exits gracefully
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Print the output regardless of exit code
            if result.stdout:
                print(f"    -> [RESULT]: {result.stdout.strip()}")
            if result.stderr:
                print(f"    -> [STDERR]: {result.stderr.strip()}")
            
            if result.returncode != 0:
                print(f"    -> [INFO] Agent exited with code {result.returncode}")
            
            if not result.stdout and not result.stderr:
                print("    -> [WARN] No output captured from agent.")
                
        except Exception as e:
            print(f"    [!] Error running container: {e}")

def execute_action(intent):
    """
    Executes the action determined by the router.
    """
    action = intent.get("action", "unknown")
    reasoning = intent.get("reasoning", "No reasoning provided.")
    
    print(f"[*] Executing Action: {action}")
    print(f"    -> [THOUGHT] {reasoning}")
    
    if action == 'get_weather':
        print(f"    -> Fetching weather for {intent.get('params', {}).get('location', 'Unknown')}...")
        print("    -> It is 22°C and Sunny.")
        
    elif action == 'save_reminder':
        print(f"    -> Saving reminder: {intent.get('params', {}).get('content', 'Unknown')}")
        print("    -> Reminder saved.")
        
    elif action == 'control_lights':
        params = intent.get('params', {})
        print(f"    -> Turning {params.get('state', 'on')} lights in {params.get('location', 'room')}...")
        print("    -> Lights controlled.")

    elif action in ["solve_task", "spawn_agent"]:
        task_spec = intent.get("params", {}).get("task_spec", "")
        if task_spec:
            handle_complex_task(task_spec)
        else:
            print("[!] Error: No task_spec provided for task.")
            
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
        # --- Builder Test Logic ---
        import argparse
        import sys
        import os
        
        # Ensure root directory is in path to import builder
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        parser = argparse.ArgumentParser()
        parser.add_argument("--test-builder", help="Description of task to build agent for")
        parser.add_argument("--test-search", help="Description of task to search agent for")
        args, unknown = parser.parse_known_args()

        if args.test_builder or args.test_search:
            from builder.search_tool import AgentSearchTool
            from builder.controller import SubAgentController
            import subprocess

            task = args.test_builder or args.test_search
            search_tool = AgentSearchTool()
            
            print(f"[*] Main Agent: Received task '{task}'")
            
            # 1. Search
            agent_image = search_tool.search(task)
            
            if agent_image:
                 print(f"[*] Agent found: {agent_image}")
            else:
                 print(f"[*] Agent MISS. Delegating to Sub-Agent Controller...")
                 if args.test_builder:
                     controller = SubAgentController()
                     agent_image = controller.create_agent(task)
                     print(f"[*] New Agent Created: {agent_image}")
                 else:
                     print("[*] Search only mode. Exiting.")
                     sys.exit(0)

            # 2. Run (if in builder mode)
            if args.test_builder and agent_image:
                print(f"[*] Executing Agent: {agent_image}")
                run_cmd = ["docker", "run", "--rm", agent_image]
                # Heuristic argument passing for demo
                task_lower = task.lower()
                if "factorial" in task_lower:
                    run_cmd.append("10") # Test value
                elif "fibonacci" in task_lower:
                    run_cmd.append("10")
                    
                try:
                    subprocess.run(run_cmd, check=True)
                except Exception as e:
                    print(f"[!] execution failed: {e}")
            sys.exit(0) 
        # --- End Builder Test ---

        while True:
            # 1. Listen
            text = transcribe_audio() # Changed from listen_command() to transcribe_audio() to match original
            if not text: continue
            
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
