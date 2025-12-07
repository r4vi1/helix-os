import requests
import json

REGISTRY_URL = "http://localhost:5001/v2"

class AgentSearchTool:
    def __init__(self, registry_url=REGISTRY_URL):
        self.registry_url = registry_url

    def list_agents(self):
        """
        Lists all repositories (agents) in the local registry.
        """
        try:
            response = requests.get(f"{self.registry_url}/_catalog")
            response.raise_for_status()
            data = response.json()
            return data.get("repositories", [])
        except Exception as e:
            print(f"[!] Error listing agents: {e}")
            return []

    def get_agent_metadata(self, agent_name, tag="latest"):
        """
        Fetches the metadata (labels) for a specific agent image.
        """
        try:
            # 1. Get Manifest to find config blob digest
            manifest_url = f"{self.registry_url}/{agent_name}/manifests/{tag}"
            headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
            response = requests.get(manifest_url, headers=headers)
            response.raise_for_status()
            manifest = response.json()
            
            config_digest = manifest["config"]["digest"]
            
            # 2. Get Config Blob
            blob_url = f"{self.registry_url}/{agent_name}/blobs/{config_digest}"
            response = requests.get(blob_url)
            response.raise_for_status()
            config_data = response.json()
            
            # 3. Extract Labels
            return config_data.get("config", {}).get("Labels", {})
            
        except Exception as e:
            print(f"[!] Error fetching metadata for {agent_name}: {e}")
            return {}

    def search(self, task_description):
        """
        Searches for an agent that matches the task description based on metadata.
        Returns the image name (e.g., 'localhost:5000/agent-fibonacci:latest') or None.
        """
        print(f"[*] Searching registry for agent matching: '{task_description}'")
        agents = self.list_agents()
        
        best_match = None
        # Simple fuzzy match for MVP. In production, use LLM or Vector DB.
        # Check if any keyword in task description matches 'helix.task' label
        task_keywords = set(task_description.lower().split())
        
        for agent in agents:
            metadata = self.get_agent_metadata(agent)
            agent_task = metadata.get("helix.task", "").lower()
            capabilities = metadata.get("helix.capabilities", "").lower()
            
            # Basic keyword overlap check
            score = 0
            if agent_task:
                score += sum(1 for word in task_keywords if word in agent_task) * 2
            if capabilities:
                score += sum(1 for word in task_keywords if word in capabilities)
                
            if score > 0:
                print(f"    -> Candidate: {agent} (Score: {score}) | Task: {agent_task}")
                if best_match is None or score > best_match[1]:
                    best_match = (agent, score)

        if best_match:
            print(f"[*] Found match: {best_match[0]}")
            return f"localhost:5000/{best_match[0]}:latest"
            
        print("[*] No suitable agent found in registry.")
        return None
