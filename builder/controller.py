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
        Orchestrates the full creation pipeline: Generate -> Compile -> build -> Push.
        """
        print(f"[*] Sub-Agent Controller: Creating agent for '{task_description}'")
        
        # 1. Generate Code
        go_code = self.generator.generate_go_code(task_description)
        # print(f"[DEBUG] Generated Code:\n{go_code}")
        
        # 2. Compile
        binary_data = self.compiler.compile_in_docker(go_code)
        
        # 3. Prepare Metadata
        agent_name = "agent-" + str(int(time.time())) # Simple unique ID
        metadata = {
            "helix.task": task_description,
            "helix.created": str(time.time()),
            "helix.capabilities": "generated, tinygo",
            "helix.author": "gemini-3-pro-preview"
        }
        
        # 4. Dockerize & Push
        image_tag = self.dockerizer.build_and_push(binary_data, agent_name, metadata)
        
        return image_tag
