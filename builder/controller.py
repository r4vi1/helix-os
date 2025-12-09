import time
from .generator import CodeGenerator
from .compiler import Compiler
from .dockerizer import Dockerizer

class SubAgentController:
    def __init__(self):
        self.generator = CodeGenerator()
        self.compiler = Compiler()
        self.dockerizer = Dockerizer()

    def _call_llm(self, prompt):
        """Helper to call Gemini for internal controller logic."""
        # Use the generator's helper if available, or duplicate logic for now.
        # Since logic is in Generator, let's reuse it via a temporary instance or move helper to utils.
        # For MVP, we'll access the private method on the generator instance.
        return self.generator._call_llm(prompt)

    def refine_task(self, raw_task):
        """
        Step 1: Refine the user's raw prompt into a precise technical specification.
        """
        print(f"    -> [Refine] Optimizing prompt: '{raw_task}'")
        prompt = f"""
        You are an expert Technical Project Manager.
        Refine the following user request into a precise, unambiguous task specification for a specialized autonomous agent.
        
        User Request: "{raw_task}"
        
        Rules:
        1. Clarify vague intents (e.g., "internet history" -> "chronological timeline of internet protocols and milestones").
        2. Specify desired depth and format.
        3. Do NOT solve the task. Only DESCRIBE the task.
        4. Output ONLY the refined task string.
        """
        refined_task = self._call_llm(prompt).strip()
        print(f"    -> [Refine] Refined Task: '{refined_task}'")
        return refined_task

    def classify_task(self, refined_task):
        """
        Step 2: Classify the task to determine the best agent type and tools.
        """
        print(f"    -> [Classify] Determining agent type for: '{refined_task}'")
        
        # In a real system, this would be an LLM call. For MVP, we'll use a strong prompt.
        prompt = f"""
        You are an System Architect. Classify the following task into one of the available agent types.
        
        Task: "{refined_task}"
        
        Available Types:
        - research_agent: Web search, fact checking, synthesis (Needs: GOOGLE_SEARCH_API_KEY)
        - compute_agent: Math, logic, precise calculations (Needs: None)
        - data_agent: Fetching, parsing, transforming data (Needs: None)
        - code_agent: Generating or executing code (Needs: None)
        - synthesis_agent: Creative writing, analysis, reasoning (Needs: GEMINI_API_KEY)
        
        Output valid JSON ONLY:
        {{
            "agent_type": "research_agent",
            "required_apis": ["API_NAME"],
            "reasoning": "One sentence reason"
        }}
        """
        response_json = self._call_llm(prompt)
        
        # Clean JSON markdown if present
        if "```json" in response_json:
            response_json = response_json.split("```json")[1].split("```")[0].strip()
        elif "```" in response_json:
            response_json = response_json.split("```")[1].split("```")[0].strip()

        import json
        try:
            classification = json.loads(response_json)
        except json.JSONDecodeError:
            print(f"    [!] Failed to parse classification JSON. Defaulting to synthesis_agent.")
            classification = {
                "agent_type": "synthesis_agent", 
                "required_apis": ["GEMINI_API_KEY"], 
                "reasoning": "Fallback due to parse error"
            }
            
        print(f"    -> [Classify] Type: {classification['agent_type']} | APIs: {classification.get('required_apis')}")
        return classification

    def create_agent(self, raw_task_description):
        """
        Orchestrates the full creation pipeline:
        1. Refine Task
        2. Classify (Select Agent Type & Tools)
        3. Build & Deploy (Loop)
        """
        print(f"[*] Sub-Agent Controller: Processing request '{raw_task_description}'")
        
        # 1. Refine
        refined_task = self.refine_task(raw_task_description)
        
        # 2. Classify
        classification = self.classify_task(refined_task)
        agent_type = classification["agent_type"]
        required_apis = classification.get("required_apis", [])
        
        # Load schema
        from .schemas import AGENT_SCHEMAS
        output_schema = AGENT_SCHEMAS.get(agent_type, AGENT_SCHEMAS["synthesis_agent"])
        
        max_retries = 2
        attempt = 0
        current_code = None
        binary_data = None
        
        # --- Phase 1: Code & Compilation ---
        while attempt <= max_retries:
            try:
                if not current_code:
                    # Pass full context to generator
                    current_code = self.generator.generate_go_code(
                        task_spec=refined_task,
                        agent_type=agent_type,
                        required_apis=required_apis,
                        output_schema=output_schema
                    )
                
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
        attempt_p2 = 0
        while attempt_p2 <= max_retries:
            try:
                agent_name = "agent-" + str(int(time.time()))
                metadata = {
                    "task": refined_task, # Use refined task
                    "capabilities": f"{agent_type}, net-enabled",
                    "helix.task": refined_task,
                    "helix.created": str(time.time()),
                    "helix.capabilities": f"{agent_type}, net-enabled",
                    "helix.author": "gemini-2.5-flash", 
                    "helix.type": agent_type
                }

                print(f"    -> [Image Init] Building Docker Image... (Attempt {attempt_p2+1})")
                image_tag = self.dockerizer.build_and_push(binary_data, agent_name, metadata)
                
                # Verify
                self.dockerizer.verify_image(image_tag)
                
                print(f"[*] Agent successfully created and verified: {image_tag}")
                return image_tag
                
            except Exception as e:
                print(f"    [!] Phase 2 (Container/Verify) Error: {e}")
                attempt_p2 += 1
                if attempt_p2 <= max_retries:
                    print("    -> [Retry] Retrying Docker build & Verification...")
                    time.sleep(1) # Short backoff
                    continue
                else:
                    print("[!] Max retries reached for Container Phase.")
                    raise
