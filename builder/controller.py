import time
from .generator import CodeGenerator
from .compiler import Compiler
from .dockerizer import Dockerizer

class SubAgentController:
    def __init__(self):
        self.generator = CodeGenerator()
        self.compiler = Compiler()
        self.dockerizer = Dockerizer()

    def create_agent(self, task_description):
        """
        Orchestrates the full creation pipeline with Retries and Self-Healing.
        Loop:
          1. Generate Code
          2. Compile (Retry with LLM fix if fails)
          3. Build Image
          4. Verify Image (Retry build/code if fails)
          5. Push
        """
        print(f"[*] Sub-Agent Controller: Creating agent for '{task_description}'")
        
        max_retries = 2
        attempt = 0
        current_code = None
        
        # --- Phase 1: Code & Compilation ---
        while attempt <= max_retries:
            try:
                if not current_code:
                    # Initial Generation
                    current_code = self.generator.generate_go_code(task_description)
                
                print(f"    -> [Build attempt {attempt+1}] Compiling...")
                binary_data = self.compiler.compile_in_docker(current_code)
                print("    -> [Success] Compilation successful.")
                break # Move to Phase 2
                
            except Exception as e:
                print(f"    [!] Compilation/Build Error: {e}")
                attempt += 1
                if attempt <= max_retries:
                    print("    -> [Self-Healing] Asking LLM to fix code...")
                    try:
                        # Feed error back to generator
                        current_code = self.generator.fix_code(current_code, str(e))
                    except Exception as llm_e:
                        print(f"    [!] Failed to get fix from LLM: {llm_e}")
                        raise
                else:
                    print("[!] Max retries reached for compilation.")
                    raise

        # --- Phase 2: Containerization & Verification ---
        # Note: metadata dictionary bugfix included here
        agent_name = "agent-" + str(int(time.time()))
        metadata = {
            "task": task_description, # FIXED: Added 'task' key which was missing
            "helix.task": task_description,
            "helix.created": str(time.time()),
            "helix.capabilities": "generated, tinygo",
            "helix.author": "gemini-3-pro-preview"
        }

        # Build but don't push yet (in a real registry we might push a temp tag, 
        # but here we build local then push)
        # We need to modify dockerizer to support verify before push if possible,
        # but our current dockerizer builds and pushes in one go.
        # For this step, we will use the verification method we added.
        
        try:
            image_tag = self.dockerizer.build_and_push(binary_data, agent_name, metadata)
            
            # Verify
            self.dockerizer.verify_image(image_tag)
            
            print(f"[*] Agent successfully created and verified: {image_tag}")
            return image_tag
            
        except Exception as e:
            print(f"[!] Container Verification failed: {e}")
            # In a full implemented controller, we might retry the whole loop here too.
            raise
