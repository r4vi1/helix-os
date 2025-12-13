"""
Memory Manager
==============
Unified API for the three-tier memory system.
This is the main interface for the Main Agent.
"""

from typing import List, Optional, Union, Any, Dict
from datetime import datetime

from .schemas import TaskMemory, AgentCapability, MemoryTier, MemoryEntry
from .working import WorkingMemory
from .episodic import EpisodicMemory
from .semantic import SemanticMemory


class MemoryManager:
    """
    Unified memory manager for the Main Agent.
    
    Provides a single API to interact with all memory tiers:
    - Working: In-session context
    - Episodic: Task history
    - Semantic: Learned patterns
    
    Usage:
        memory = MemoryManager()
        
        # Store a task result
        memory.store("episodic", TaskMemory(raw_task="research AI", ...))
        
        # Recall similar experiences
        results = memory.recall("AI research", limit=5)
        
        # Get context for sub-agent
        context = memory.get_context_for_subagent("research web history")
    """
    
    def __init__(self, db_path: Optional[str] = None, buffer_minutes: int = 5):
        """
        Initialize the memory manager.
        
        Args:
            db_path: Path to SQLite database (default: ~/.helix/memory.db)
            buffer_minutes: Passive mode buffer duration
        """
        self.working = WorkingMemory(buffer_minutes=buffer_minutes)
        self.episodic = EpisodicMemory(db_path=db_path)
        self.semantic = SemanticMemory(db_path=db_path)
        
        # Lazy-loaded controllers
        self._lifecycle_controller = None
        self._context_slicer = None
        self._cleanup = None
    
    @property
    def lifecycle(self):
        """Get lifecycle controller (lazy loaded)."""
        if self._lifecycle_controller is None:
            from .lifecycle_controller import MemoryLifecycleController
            self._lifecycle_controller = MemoryLifecycleController(self)
        return self._lifecycle_controller
    
    @property
    def slicer(self):
        """Get context slicer (lazy loaded)."""
        if self._context_slicer is None:
            from .context_slicer import ContextSlicer
            self._context_slicer = ContextSlicer(self)
        return self._context_slicer
    
    @property
    def cleaner(self):
        """Get cleanup manager (lazy loaded)."""
        if self._cleanup is None:
            from .cleanup import MemoryCleanup
            self._cleanup = MemoryCleanup(self)
        return self._cleanup
    
    # ==================== STORE ====================
    
    def store(self, memory_type: str, data: Union[MemoryEntry, Dict[str, Any]]) -> str:
        """
        Store data in the specified memory tier.
        
        Args:
            memory_type: "working", "episodic", or "semantic"
            data: Memory entry or dict to store
            
        Returns:
            ID of stored memory (or key for working memory)
        """
        if memory_type == "working":
            if isinstance(data, dict):
                key = data.get("key", str(datetime.now().timestamp()))
                self.working.store(key, data)
                return key
            elif isinstance(data, TaskMemory):
                self.working.set_current_task(data)
                return data.id
                
        elif memory_type == "episodic":
            if isinstance(data, TaskMemory):
                return self.episodic.store(data)
            elif isinstance(data, dict):
                memory = TaskMemory(**data)
                return self.episodic.store(memory)
                
        elif memory_type == "semantic":
            if isinstance(data, AgentCapability):
                return self.semantic.store(data)
            elif isinstance(data, dict):
                capability = AgentCapability(**data)
                return self.semantic.store(capability)
        
        raise ValueError(f"Unknown memory type: {memory_type}")
    
    # ==================== RECALL ====================
    
    def recall(
        self, 
        query: str, 
        memory_type: Optional[str] = None, 
        limit: int = 5
    ) -> List[MemoryEntry]:
        """
        Recall memories similar to query.
        
        Args:
            query: Search query (uses semantic similarity)
            memory_type: Optional filter ("working", "episodic", "semantic", or None for all)
            limit: Maximum results per tier
            
        Returns:
            List of matching memory entries
        """
        results = []
        
        if memory_type in (None, "episodic"):
            results.extend(self.episodic.recall_similar(query, limit=limit))
        
        if memory_type in (None, "semantic"):
            results.extend(self.semantic.recall_similar(query, limit=limit))
        
        if memory_type == "working":
            # Working memory doesn't have semantic search - return current context
            current = self.working.get_current_task()
            if current:
                results.append(current)
        
        return results[:limit]
    
    def recall_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """Recall a specific memory by ID."""
        # Try episodic first
        result = self.episodic.recall_by_id(memory_id)
        if result:
            return result
        
        # Try working memory
        result = self.working.recall(memory_id)
        if result:
            return result
        
        return None
    
    # ==================== TASK LIFECYCLE ====================
    
    def start_task(self, raw_task: str, refined_task: str = "", agent_type: str = "") -> TaskMemory:
        """
        Start tracking a new task in working memory.
        
        Args:
            raw_task: Original user request
            refined_task: Refined task specification
            agent_type: Type of agent handling this
            
        Returns:
            TaskMemory object for this task
        """
        task = TaskMemory(
            raw_task=raw_task,
            refined_task=refined_task or raw_task,
            agent_type=agent_type,
            outcome="pending",
            current_tier=MemoryTier.WORKING
        )
        self.working.set_current_task(task)
        return task
    
    def complete_task(
        self, 
        outcome: str = "success",
        result_summary: Optional[str] = None,
        execution_time_ms: int = 0,
        agent_image: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[str]:
        """
        Complete current task and promote to episodic memory.
        
        Returns:
            Memory ID if stored, None if no current task
        """
        task = self.working.clear_current_task()
        if not task:
            return None
        
        # Update task with results
        task.outcome = outcome
        task.result_summary = result_summary
        task.execution_time_ms = execution_time_ms
        task.agent_image = agent_image
        task.error_message = error_message
        task.current_tier = MemoryTier.EPISODIC
        
        # Store in episodic
        memory_id = self.episodic.store(task)
        
        # Update semantic stats
        self.semantic.update_from_execution(
            agent_type=task.agent_type,
            success=(outcome == "success"),
            execution_time_ms=execution_time_ms
        )
        
        return memory_id
    
    # ==================== CONTEXT FOR SUB-AGENTS ====================
    
    def get_context_for_subagent(self, task_spec: str, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get context slice to inject into sub-agent prompt.
        
        This is the key interface for main-agent → sub-agent context passing.
        """
        return self.slicer.slice_for_task(task_spec, agent_type)
    
    def format_context_for_prompt(self, task_spec: str, agent_type: Optional[str] = None) -> str:
        """Get formatted context string for prompt injection."""
        context = self.get_context_for_subagent(task_spec, agent_type)
        return self.slicer.format_for_prompt(context)
    
    # ==================== MAINTENANCE ====================
    
    def run_lifecycle(self) -> dict:
        """Run lifecycle controller to transition memories between tiers."""
        return self.lifecycle.run_lifecycle_pass()
    
    def run_cleanup(self) -> dict:
        """Run garbage collection."""
        return self.cleaner.run_full_cleanup()
    
    def consolidate(self):
        """Consolidate working memory to disk (call on session end)."""
        # Complete any pending task
        current = self.working.get_current_task()
        if current and current.outcome == "pending":
            self.complete_task(outcome="partial", result_summary="Session ended")
        
        # Run lifecycle pass
        self.run_lifecycle()
    
    # ==================== PASSIVE MODE ====================
    
    def add_passive_transcription(self, text: str):
        """Add transcription to passive mode buffer."""
        self.working.add_to_passive_buffer(text)
    
    def get_passive_buffer(self) -> str:
        """Get current passive buffer contents."""
        return self.working.get_passive_buffer()
    
    # ==================== STATS ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            "episodic_count": len(self.episodic.get_all()),
            "semantic_count": len(self.semantic.get_all()),
            "working_has_task": self.working.get_current_task() is not None,
            "passive_buffer_size": len(self.working.context.passive_buffer)
        }
