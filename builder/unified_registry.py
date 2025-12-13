"""
Unified Agent Registry
======================
Search wrapper over both K8s (Docker) and WASM registries.
Returns best match with runtime type discriminator.
"""

from dataclasses import dataclass
from typing import Optional, Literal, List

from .search_tool import AgentSearchTool
from .wasm_registry import WASMRegistry


@dataclass
class AgentMatch:
    """Result of a unified registry search."""
    name: str
    runtime: Literal["k8s", "wasm"]
    reference: str  # Docker image tag or WASM path
    score: float
    task: str  # The task description stored for this agent
    capabilities: List[str] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class UnifiedAgentRegistry:
    """
    Unified search interface over both K8s and WASM registries.
    
    Searches both registries and returns the best match,
    along with the runtime type needed to execute it.
    """
    
    def __init__(
        self, 
        k8s_registry: AgentSearchTool = None,
        wasm_registry: WASMRegistry = None
    ):
        self.k8s_registry = k8s_registry or AgentSearchTool()
        self.wasm_registry = wasm_registry or WASMRegistry()
    
    def search(self, task_description: str, runtime_filter: str = None) -> Optional[AgentMatch]:
        """
        Search both registries for an agent matching the task.
        
        Returns the best match across both registries, with runtime
        type indicating whether to use K8s or WASM execution.
        
        Args:
            task_description: Description of the task to find an agent for
            runtime_filter: Optional "k8s" or "wasm" to limit search to one registry
        
        Returns:
            AgentMatch with runtime type, or None if no match found
        """
        print(f"\n[*] Unified search for: '{task_description}'")
        
        k8s_match = None
        wasm_match = None
        
        # Search based on filter
        if runtime_filter != "wasm":
            k8s_match = self._search_k8s(task_description)
        if runtime_filter != "k8s":
            wasm_match = self._search_wasm(task_description)
        
        # If neither found anything
        if not k8s_match and not wasm_match:
            print("[*] No agent found in either registry.")
            return None
        
        # If only one found something
        if k8s_match and not wasm_match:
            print(f"[*] Best match: K8s agent '{k8s_match.name}' (score: {k8s_match.score:.2f})")
            return k8s_match
        
        if wasm_match and not k8s_match:
            print(f"[*] Best match: WASM agent '{wasm_match.name}' (score: {wasm_match.score:.2f})")
            return wasm_match
        
        # Both found something - pick the best
        best = self._pick_best(k8s_match, wasm_match)
        print(f"[*] Best match: {best.runtime.upper()} agent '{best.name}' (score: {best.score:.2f})")
        return best
    
    def _search_k8s(self, task_description: str) -> Optional[AgentMatch]:
        """Search K8s (Docker) registry."""
        agents = self.k8s_registry.list_agents()
        
        if not agents:
            return None
        
        # Use same algorithm as original search
        stop_words = {"the", "a", "an", "of", "to", "for", "and", "or", "in", "on", "at", "is", "it", "be", "as"}
        task_lower = task_description.lower()
        task_keywords = set(
            word.lower() for word in task_description.split() 
            if word.lower() not in stop_words and len(word) > 2
        )
        
        best_match = None
        best_score = 0
        best_task = ""
        
        for agent in agents:
            metadata = self.k8s_registry.get_agent_metadata(agent)
            agent_task = metadata.get("helix.task", "").lower()
            
            if not agent_task:
                continue
            
            agent_keywords = set(
                word.lower() for word in agent_task.split() 
                if word.lower() not in stop_words and len(word) > 2
            )
            
            if agent_keywords and task_keywords:
                intersection = task_keywords.intersection(agent_keywords)
                union = task_keywords.union(agent_keywords)
                score = len(intersection) / len(union) if union else 0
                
                # Bonus for type match
                agent_name_lower = agent.lower()
                for kw in ["research", "compute", "data", "code", "synthesis"]:
                    if kw in task_lower and kw in agent_name_lower:
                        score += 0.3
                        break
                
                # Bonus for helix-prefixed agents
                if agent_name_lower.startswith("helix-"):
                    score += 0.5
                
                if score > best_score:
                    best_score = score
                    best_match = agent
                    best_task = metadata.get("helix.task", "")
        
        if best_match and best_score >= 0.2:
            return AgentMatch(
                name=best_match,
                runtime="k8s",
                reference=f"localhost:5001/{best_match}:latest",
                score=best_score,
                task=best_task
            )
        
        return None
    
    def _search_wasm(self, task_description: str) -> Optional[AgentMatch]:
        """Search WASM registry."""
        agent_name = self.wasm_registry.search(task_description)
        
        if not agent_name:
            return None
        
        # Get metadata to calculate score (search already did this, but we need details)
        metadata = self.wasm_registry.get_agent_metadata(agent_name)
        wasm_path = self.wasm_registry.get_wasm_path(agent_name)
        
        # Recalculate score for comparison
        stop_words = {"the", "a", "an", "of", "to", "for", "and", "or", "in", "on", "at", "is", "it", "be", "as"}
        task_keywords = set(
            word.lower() for word in task_description.split() 
            if word.lower() not in stop_words and len(word) > 2
        )
        
        agent_task = metadata.get("helix.task", "").lower()
        agent_keywords = set(
            word.lower() for word in agent_task.split() 
            if word.lower() not in stop_words and len(word) > 2
        )
        
        if agent_keywords and task_keywords:
            intersection = task_keywords.intersection(agent_keywords)
            union = task_keywords.union(agent_keywords)
            score = len(intersection) / len(union) if union else 0
        else:
            score = 0.2  # Minimum threshold (since search passed)
        
        return AgentMatch(
            name=agent_name,
            runtime="wasm",
            reference=str(wasm_path) if wasm_path else agent_name,
            score=score,
            task=metadata.get("helix.task", ""),
            capabilities=metadata.get("helix.capabilities", "").split(",")
        )
    
    def _pick_best(self, k8s: AgentMatch, wasm: AgentMatch) -> AgentMatch:
        """
        Pick the best match between K8s and WASM agents.
        
        Tie-breaking rules:
        1. Higher score wins
        2. If scores are close (within 0.1), prefer WASM (faster execution)
        3. If WASM score is much lower, use K8s (more reliable)
        """
        score_diff = k8s.score - wasm.score
        
        # If K8s is significantly better, use it
        if score_diff > 0.1:
            return k8s
        
        # If WASM is significantly better, use it
        if score_diff < -0.1:
            return wasm
        
        # Scores are close - prefer WASM for speed
        # (WASM has near-zero cold start vs container spin-up)
        return wasm
    
    def list_all(self) -> dict:
        """List all agents from both registries."""
        return {
            "k8s": self.k8s_registry.list_agents(),
            "wasm": self.wasm_registry.list_agents()
        }
