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
            # 404 is normal for new agents or fresh registry
            if "404" in str(e):
                return {}
            print(f"[!] Error fetching metadata for {agent_name}: {e}")
            return {}

    def search(self, task_description):
        """
        Searches for an agent that matches the task description based on metadata.
        Returns the image name (e.g., 'localhost:5001/agent-fibonacci:latest') or None.
        """
        print(f"[*] Searching registry for agent matching: '{task_description}'")
        agents = self.list_agents()
        
        if not agents:
            print("[*] No agents in registry.")
            return None
        
        # Stop words to filter out
        stop_words = {"the", "a", "an", "of", "to", "for", "and", "or", "in", "on", "at", "is", "it", "be", "as"}
        
        # Extract significant keywords from task
        task_keywords = set(word.lower() for word in task_description.split() if word.lower() not in stop_words and len(word) > 2)
        
        best_match = None
        best_score = 0
        
        for agent in agents:
            metadata = self.get_agent_metadata(agent)
            agent_task = metadata.get("helix.task", "").lower()
            
            if not agent_task:
                continue
            
            # Extract keywords from stored task
            agent_keywords = set(word.lower() for word in agent_task.split() if word.lower() not in stop_words and len(word) > 2)
            
            # Calculate overlap ratio (Jaccard-like similarity)
            if agent_keywords and task_keywords:
                intersection = task_keywords.intersection(agent_keywords)
                union = task_keywords.union(agent_keywords)
                score = len(intersection) / len(union) if union else 0
                
                print(f"    -> Candidate: {agent} | Stored Task: '{agent_task[:50]}...' | Overlap: {len(intersection)}/{len(union)} = {score:.2f}")
                
                if score > best_score:
                    best_score = score
                    best_match = agent

        # Threshold: At least 50% keyword overlap to consider it a match
        if best_match and best_score >= 0.5:
            print(f"[*] Found match: {best_match} (Score: {best_score:.2f})")
            return f"localhost:5001/{best_match}:latest"
            
        print(f"[*] No suitable agent found in registry (best score: {best_score:.2f}).")
        return None
