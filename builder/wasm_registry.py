"""
WASM Registry
=============
Directory-based registry for WebAssembly modules.
Mirrors the Docker registry interface for consistency.
Supports hybrid keyword + semantic search.
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict, field


@dataclass
class WASMManifest:
    """Metadata for a WASM module."""
    name: str
    task: str  # helix.task equivalent
    runtime: str = "wasm"
    capabilities: List[str] = None
    created: str = None
    wasm_file: str = "agent.wasm"
    embedding: List[float] = None  # Semantic embedding for task description
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.created is None:
            self.created = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class WASMRegistry:
    """
    Directory-based registry for WASM modules.
    
    Structure:
        ~/.helix/wasm/
        ├── fibonacci/
        │   ├── agent.wasm
        │   └── manifest.json
        ├── text-processor/
        │   ├── agent.wasm
        │   └── manifest.json
    """
    
    DEFAULT_PATH = Path.home() / ".helix" / "wasm"
    
    def __init__(self, registry_path: Path = None):
        self.registry_path = Path(registry_path) if registry_path else self.DEFAULT_PATH
        self.registry_path.mkdir(parents=True, exist_ok=True)
    
    def list_agents(self) -> List[str]:
        """
        Lists all WASM agents in the registry.
        Returns list of agent names.
        """
        agents = []
        try:
            for item in self.registry_path.iterdir():
                if item.is_dir():
                    manifest_path = item / "manifest.json"
                    wasm_path = item / "agent.wasm"
                    # Only include if both manifest and wasm exist
                    if manifest_path.exists() and wasm_path.exists():
                        agents.append(item.name)
        except Exception as e:
            print(f"[!] Error listing WASM agents: {e}")
        return agents
    
    def get_agent_metadata(self, agent_name: str) -> Dict:
        """
        Fetches the metadata (manifest) for a specific WASM agent.
        Returns dict compatible with Docker label format.
        """
        try:
            manifest_path = self.registry_path / agent_name / "manifest.json"
            if not manifest_path.exists():
                return {}
            
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            
            # Return in format compatible with Docker labels
            return {
                "helix.task": manifest.get("task", ""),
                "helix.runtime": manifest.get("runtime", "wasm"),
                "helix.capabilities": ",".join(manifest.get("capabilities", [])),
                "helix.created": manifest.get("created", ""),
            }
        except Exception as e:
            print(f"[!] Error reading WASM manifest for {agent_name}: {e}")
            return {}
    
    def get_manifest(self, agent_name: str) -> Optional[WASMManifest]:
        """Get full manifest object for an agent."""
        try:
            manifest_path = self.registry_path / agent_name / "manifest.json"
            if not manifest_path.exists():
                return None
            
            with open(manifest_path, "r") as f:
                data = json.load(f)
            
            return WASMManifest(
                name=data.get("name", agent_name),
                task=data.get("task", ""),
                runtime=data.get("runtime", "wasm"),
                capabilities=data.get("capabilities", []),
                created=data.get("created", ""),
                wasm_file=data.get("wasm_file", "agent.wasm")
            )
        except Exception as e:
            print(f"[!] Error reading WASM manifest for {agent_name}: {e}")
            return None
    
    def store(self, agent_name: str, wasm_binary: bytes, manifest: WASMManifest) -> str:
        """
        Store a WASM module in the registry.
        
        Args:
            agent_name: Name of the agent (used as directory name)
            wasm_binary: Compiled WASM binary data
            manifest: Metadata for the agent
        
        Returns:
            Path to the stored WASM file
        """
        agent_dir = self.registry_path / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Write WASM binary
        wasm_path = agent_dir / manifest.wasm_file
        with open(wasm_path, "wb") as f:
            f.write(wasm_binary)
        
        # Write manifest
        manifest_path = agent_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(asdict(manifest), f, indent=2)
        
        print(f"[*] Stored WASM agent: {agent_name} at {wasm_path}")
        return str(wasm_path)
    
    def get_wasm_path(self, agent_name: str) -> Optional[Path]:
        """Get the path to a WASM binary."""
        manifest = self.get_manifest(agent_name)
        if not manifest:
            return None
        
        wasm_path = self.registry_path / agent_name / manifest.wasm_file
        if wasm_path.exists():
            return wasm_path
        return None
    
    def get_wasm_binary(self, agent_name: str) -> Optional[bytes]:
        """Read and return the WASM binary for an agent."""
        wasm_path = self.get_wasm_path(agent_name)
        if not wasm_path:
            return None
        
        with open(wasm_path, "rb") as f:
            return f.read()
    
    def delete(self, agent_name: str) -> bool:
        """Delete an agent from the registry."""
        agent_dir = self.registry_path / agent_name
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
            print(f"[*] Deleted WASM agent: {agent_name}")
            return True
        return False
    
    @staticmethod
    def _stem(word: str) -> str:
        """
        Simple suffix-stripping stemmer for better keyword matching.
        Ensures related words (calculate/calculating/calculations) produce same stems.
        """
        word = word.lower()
        
        # Step 1: Handle compound suffixes first (longest to shortest)
        compound_suffixes = [
            ('ications', 5),  # multiplications -> multipl
            ('ational', 5),   # computational -> comput
            ('ations', 5),    # calculations -> calcul
            ('ating', 5),     # calculating -> calcul (ate+ing)
            ('uting', 5),     # computing -> comput
            ('izing', 5),     # analyzing -> analyz
            ('ising', 5),     # analysing -> analyz
            ('ition', 5),
            ('ation', 5),     # calculation -> calcul
            ('ment', 4),      # development -> develop
            ('ness', 4),      # darkness -> dark
            ('able', 4),
            ('ible', 4),
            ('ical', 4),      # mathematical -> mathemat
            ('ally', 4),
            ('ting', 4),      # computing fallback
            ('ive', 3),
            ('ful', 3),
            ('ous', 3),
            ('ize', 3),       # analyze -> analyz
            ('ise', 3),
            ('ate', 3),       # calculate -> calcul
            ('ing', 3),       # running -> runn
            ('ion', 3),
            ('ed', 2),        # computed -> comput
            ('er', 2),
            ('ly', 2),
            ('al', 2),
            ('s', 2),         # plurals last (min 2 to avoid over-stripping)
        ]
        
        for suffix, min_remain in compound_suffixes:
            if word.endswith(suffix) and len(word) - len(suffix) >= min_remain:
                word = word[:-len(suffix)]
                break
        
        # Step 2: Strip trailing 'e' for consistency (compute -> comput)
        if word.endswith('e') and len(word) > 4:
            word = word[:-1]
        
        return word
    
    @classmethod
    def _extract_stemmed_keywords(cls, text: str, stop_words: set) -> set:
        """Extract keywords from text and stem them."""
        words = text.lower().split()
        keywords = set()
        
        for word in words:
            # Clean word of punctuation
            word = ''.join(c for c in word if c.isalnum())
            if word not in stop_words and len(word) > 2:
                keywords.add(cls._stem(word))
        
        return keywords

    def search(self, task_description: str) -> Optional[str]:
        """
        Search for a WASM agent matching the task description.
        Uses stemming for better keyword matching.
        
        Returns agent name if found, None otherwise.
        """
        print(f"[*] Searching WASM registry for: '{task_description}'")
        agents = self.list_agents()
        
        if not agents:
            print("[*] No WASM agents in registry.")
            return None
        
        # Stop words to filter out
        stop_words = {"the", "a", "an", "of", "to", "for", "and", "or", "in", "on", "at", "is", "it", "be", "as", "with"}
        
        # Extract stemmed keywords from task
        task_lower = task_description.lower()
        task_keywords = self._extract_stemmed_keywords(task_description, stop_words)
        
        best_match = None
        best_score = 0
        
        for agent in agents:
            metadata = self.get_agent_metadata(agent)
            agent_task = metadata.get("helix.task", "")
            
            if not agent_task:
                continue
            
            # Extract stemmed keywords from stored task
            agent_keywords = self._extract_stemmed_keywords(agent_task, stop_words)
            
            # Calculate overlap ratio (Jaccard similarity)
            if agent_keywords and task_keywords:
                intersection = task_keywords.intersection(agent_keywords)
                union = task_keywords.union(agent_keywords)
                score = len(intersection) / len(union) if union else 0
                
                # Bonus for type match in agent name
                agent_name_lower = agent.lower()
                for kw in ["research", "compute", "data", "code", "synthesis", "math", "text"]:
                    if kw in task_lower and kw in agent_name_lower:
                        score += 0.3
                        break
                
                print(f"    -> WASM Candidate: {agent} | Task: '{agent_task[:40]}...' | Score: {score:.2f}")
                
                if score > best_score:
                    best_score = score
                    best_match = agent
        
        # Threshold for match
        if best_match and best_score >= 0.2:
            print(f"[*] Found WASM match: {best_match} (Score: {best_score:.2f})")
            return best_match
        
        print(f"[*] No suitable WASM agent found (best score: {best_score:.2f}).")
        return None

    def semantic_search(
        self, 
        task_description: str, 
        alpha: float = 0.5
    ) -> Tuple[Optional[str], float]:
        """
        Hybrid search combining keyword matching and semantic similarity.
        
        Args:
            task_description: The task to search for
            alpha: Weight for keyword score (1-alpha for semantic)
                   0.0 = pure semantic, 1.0 = pure keyword, 0.5 = balanced
        
        Returns:
            Tuple of (agent_name, combined_score) or (None, 0.0)
        """
        print(f"[*] Semantic search for: '{task_description}'")
        agents = self.list_agents()
        
        if not agents:
            print("[*] No WASM agents in registry.")
            return None, 0.0
        
        # Import embeddings module
        try:
            from memory.embeddings import embed, similarity
            embeddings_available = True
        except ImportError:
            print("[WARN] Embeddings not available, falling back to keyword-only search.")
            embeddings_available = False
            alpha = 1.0  # Force keyword-only
        
        # Compute query embedding if available
        query_embedding = None
        if embeddings_available and alpha < 1.0:
            query_embedding = embed(task_description)
        
        # Stop words for keyword matching
        stop_words = {"the", "a", "an", "of", "to", "for", "and", "or", "in", "on", "at", "is", "it", "be", "as", "with"}
        task_keywords = self._extract_stemmed_keywords(task_description, stop_words)
        task_lower = task_description.lower()
        
        best_match = None
        best_score = 0.0
        
        for agent in agents:
            manifest = self.get_manifest(agent)
            if not manifest or not manifest.task:
                continue
            
            # Keyword score (Jaccard similarity with stemming)
            agent_keywords = self._extract_stemmed_keywords(manifest.task, stop_words)
            keyword_score = 0.0
            if agent_keywords and task_keywords:
                intersection = task_keywords.intersection(agent_keywords)
                union = task_keywords.union(agent_keywords)
                keyword_score = len(intersection) / len(union) if union else 0
                
                # Bonus for type match in agent name
                agent_name_lower = agent.lower()
                for kw in ["research", "compute", "data", "code", "synthesis", "math", "text"]:
                    if kw in task_lower and kw in agent_name_lower:
                        keyword_score = min(1.0, keyword_score + 0.3)
                        break
            
            # Semantic score (cosine similarity)
            semantic_score = 0.0
            if embeddings_available and query_embedding and alpha < 1.0:
                agent_embedding = manifest.embedding
                if agent_embedding:
                    semantic_score = similarity(query_embedding, agent_embedding)
                else:
                    # Compute on-the-fly if not stored
                    agent_embedding = embed(manifest.task)
                    semantic_score = similarity(query_embedding, agent_embedding)
            
            # Combined score
            combined_score = (alpha * keyword_score) + ((1 - alpha) * semantic_score)
            
            print(f"    -> {agent} | KW: {keyword_score:.2f} | Sem: {semantic_score:.2f} | Combined: {combined_score:.2f}")
            
            if combined_score > best_score:
                best_score = combined_score
                best_match = agent
        
        # Threshold for match
        if best_match and best_score >= 0.2:
            print(f"[*] Found semantic match: {best_match} (Score: {best_score:.2f})")
            return best_match, best_score
        
        print(f"[*] No suitable agent found (best: {best_score:.2f}).")
        return None, best_score

    def store_with_embedding(
        self, 
        agent_name: str, 
        wasm_binary: bytes, 
        manifest: WASMManifest
    ) -> str:
        """
        Store a WASM module with pre-computed embedding for semantic search.
        """
        # Compute embedding for task description
        try:
            from memory.embeddings import embed
            if not manifest.embedding:
                manifest.embedding = embed(manifest.task)
                print(f"[*] Computed embedding for '{manifest.task[:30]}...'")
        except ImportError:
            print("[WARN] Embeddings not available, storing without embedding.")
        
        return self.store(agent_name, wasm_binary, manifest)
