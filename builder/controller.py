import time
from .generator import CodeGenerator
from .compiler import Compiler
from .dockerizer import Dockerizer

# Memory system integration
try:
    from memory import MemoryManager
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    print("[WARN] Memory module not available. Running without memory.")

class SubAgentController:
    def __init__(self, memory_manager=None):
        self.generator = CodeGenerator()
        self.compiler = Compiler()
        self.dockerizer = Dockerizer()
        
        # Memory integration
        if memory_manager:
            self.memory = memory_manager
        elif MEMORY_AVAILABLE:
            self.memory = MemoryManager()
        else:
            self.memory = None

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
        Step 2: Classify the task using DETERMINISTIC keyword matching.
        No LLM calls - predictable and consistent.
        """
        print(f"    -> [Classify] Determining agent type for: '{refined_task[:80]}...'")
        
        task_lower = refined_task.lower()
        
        # RESEARCH patterns - highest priority for information gathering
        research_keywords = [
            "research", "history", "find out", "look up", "search for",
            "what is", "who is", "when did", "where is", "how did",
            "facts about", "information about", "tell me about",
            "investigate", "discover", "learn about", "explore",
            "timeline", "origins", "evolution", "development of"
        ]
        
        # COMPUTE patterns - math and logic
        compute_keywords = [
            "calculate", "compute", "fibonacci", "sum", "multiply",
            "divide", "subtract", "add", "math", "equation",
            "factorial", "prime", "average", "percentage", "solve"
        ]
        
        # DATA patterns - structured data manipulation
        data_keywords = [
            "fetch data", "parse json", "parse csv", "transform data",
            "api call", "extract from", "convert format", "data from"
        ]
        
        # CODE patterns - code generation
        code_keywords = [
            "write code", "generate code", "create script", "program",
            "function to", "implement", "code snippet", "write a function"
        ]
        
        # SYNTHESIS patterns - pure creative/reasoning (lowest priority)
        synthesis_keywords = [
            "write a poem", "write a story", "creative writing",
            "opinion on", "your thoughts", "imagine", "compose"
        ]
        
        # Check in priority order
        if any(kw in task_lower for kw in research_keywords):
            agent_type = "research_agent"
            required_apis = ["GOOGLE_SEARCH_API_KEY"]
            reasoning = "Task involves researching or finding information"
        elif any(kw in task_lower for kw in compute_keywords):
            agent_type = "compute_agent"
            required_apis = []
            reasoning = "Task involves mathematical computation"
        elif any(kw in task_lower for kw in data_keywords):
            agent_type = "data_agent"
            required_apis = []
            reasoning = "Task involves data fetching or transformation"
        elif any(kw in task_lower for kw in code_keywords):
            agent_type = "code_agent"
            required_apis = []
            reasoning = "Task involves code generation"
        elif any(kw in task_lower for kw in synthesis_keywords):
            agent_type = "synthesis_agent"
            required_apis = ["GEMINI_API_KEY"]
            reasoning = "Task involves pure creative synthesis"
        else:
            # Default to research for any informational task, synthesis for unknown
            # If task contains question words, assume research
            if any(q in task_lower for q in ["what", "who", "when", "where", "why", "how"]):
                agent_type = "research_agent"
                required_apis = ["GOOGLE_SEARCH_API_KEY"]
                reasoning = "Question-based task defaults to research"
            else:
                agent_type = "synthesis_agent"
                required_apis = ["GEMINI_API_KEY"]
                reasoning = "Default fallback for unknown task type"
        
        classification = {
            "agent_type": agent_type,
            "required_apis": required_apis,
            "reasoning": reasoning
        }
            
        print(f"    -> [Classify] Type: {classification['agent_type']} | APIs: {classification.get('required_apis')}")
        return classification

    def create_agent(self, raw_task_description):
        """
        Orchestrates the full creation pipeline:
        1. Refine Task
        2. Classify (Select Agent Type & Tools)
        3. Build & Deploy (Loop)
        
        With memory integration:
        - Starts tracking task in working memory
        - Injects context from past experiences
        - Stores result in episodic memory on completion
        """
        print(f"[*] Sub-Agent Controller: Processing request '{raw_task_description}'")
        start_time = time.time()
        
        # 1. Refine
        refined_task = self.refine_task(raw_task_description)
        
        # 2. Classify
        classification = self.classify_task(refined_task)
        agent_type = classification["agent_type"]
        required_apis = classification.get("required_apis", [])
        
        # --- Memory: Start tracking task ---
        if self.memory:
            self.memory.start_task(
                raw_task=raw_task_description,
                refined_task=refined_task,
                agent_type=agent_type
            )
            # Get context from past experiences for prompt injection
            context = self.memory.format_context_for_prompt(refined_task, agent_type)
            if context:
                print(f"    -> [Memory] Injecting context from {len(self.memory.recall(refined_task, 'episodic', limit=3))} past experiences")
        else:
            context = ""
        
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
                    # Pass full context (including memory) to generator
                    current_code = self.generator.generate_go_code(
                        task_spec=refined_task,
                        agent_type=agent_type,
                        required_apis=required_apis,
                        output_schema=output_schema,
                        memory_context=context
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
                # Semantic naming: helix-research-agent, helix-compute-agent, etc.
                type_short = agent_type.replace("_agent", "")
                agent_name = f"helix-{type_short}-agent-{int(time.time())}"
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
                
                # --- Memory: Store success ---
                if self.memory:
                    execution_time = int((time.time() - start_time) * 1000)
                    self.memory.complete_task(
                        outcome="success",
                        result_summary=f"Created agent: {image_tag}",
                        execution_time_ms=execution_time,
                        agent_image=image_tag
                    )
                    print(f"    -> [Memory] Task stored in episodic memory")
                
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
                    # --- Memory: Store failure ---
                    if self.memory:
                        execution_time = int((time.time() - start_time) * 1000)
                        self.memory.complete_task(
                            outcome="failure",
                            error_message=str(e),
                            execution_time_ms=execution_time
                        )
                    print("[!] Max retries reached for Container Phase.")
                    raise

