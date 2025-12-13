"""
Memory Lifecycle Controller
===========================
Autoclass-inspired automatic tier transitions.
"""

import math
from datetime import datetime, timedelta
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import MemoryManager

from .schemas import MemoryEntry, TaskMemory, AgentCapability, MemoryTier


class MemoryLifecycleController:
    """
    Manages automatic memory tier transitions based on access patterns.
    Inspired by GCP Autoclass.
    """
    
    # Score thresholds for tier placement
    THRESHOLDS = {
        "working": 0.7,   # Hot - keep in RAM
        "episodic": 0.4,  # Warm - keep in SQLite
        "semantic": 0.2,  # Cold - distill to patterns
        "archive": 0.0    # Frozen - compress and archive
    }
    
    def __init__(self, memory_manager: "MemoryManager"):
        self.memory = memory_manager
        self._last_run: Optional[datetime] = None
    
    def calculate_lifecycle_score(self, entry: MemoryEntry) -> float:
        """
        Calculate lifecycle score (0.0 to 1.0) for tier placement.
        
        Factors:
        - Recency (30%): When was it last accessed?
        - Frequency (20%): How often is it accessed?
        - Relevance (30%): Semantic similarity to recent tasks
        - Success (20%): If applicable, task success rate
        """
        now = datetime.now()
        
        # Recency: exponential decay with ~7 day half-life
        days_since_access = (now - entry.last_accessed).days
        recency_score = math.exp(-days_since_access / 7)
        
        # Frequency: normalized access count (cap at 10)
        frequency_score = min(entry.access_count / 10.0, 1.0)
        
        # Relevance: similarity to recent tasks (simplified - use working memory context)
        relevance_score = self._calculate_relevance(entry)
        
        # Success: for task memories
        if hasattr(entry, 'success_rate'):
            success_score = entry.success_rate
        else:
            success_score = 0.5  # Neutral for non-task memories
        
        # Weighted combination
        score = (
            0.3 * recency_score +
            0.2 * frequency_score +
            0.3 * relevance_score +
            0.2 * success_score
        )
        
        return min(max(score, 0.0), 1.0)
    
    def _calculate_relevance(self, entry: MemoryEntry) -> float:
        """Calculate relevance to current context."""
        from . import embeddings
        
        # Get current task from working memory
        current = self.memory.working.get_current_task()
        if not current or not hasattr(current, 'refined_task'):
            return 0.5  # Neutral if no current context
        
        # Compare embeddings
        if entry.embedding and hasattr(current, 'refined_task'):
            current_embedding = embeddings.embed(current.refined_task)
            return embeddings.similarity(entry.embedding, current_embedding)
        
        return 0.5
    
    def score_to_tier(self, score: float) -> MemoryTier:
        """Convert score to target tier."""
        if score >= self.THRESHOLDS["working"]:
            return MemoryTier.WORKING
        elif score >= self.THRESHOLDS["episodic"]:
            return MemoryTier.EPISODIC
        elif score >= self.THRESHOLDS["semantic"]:
            return MemoryTier.SEMANTIC
        else:
            return MemoryTier.ARCHIVE
    
    def run_lifecycle_pass(self) -> dict:
        """
        Evaluate all memories and transition between tiers.
        Returns stats about transitions made.
        """
        stats = {
            "evaluated": 0,
            "promoted": 0,
            "demoted": 0,
            "archived": 0,
            "deleted": 0
        }
        
        # Process episodic memories
        for memory in self.memory.episodic.get_all():
            stats["evaluated"] += 1
            score = self.calculate_lifecycle_score(memory)
            target_tier = self.score_to_tier(score)
            
            if target_tier != memory.current_tier:
                self._transition(memory, target_tier, stats)
        
        # Process semantic memories
        for memory in self.memory.semantic.get_all():
            stats["evaluated"] += 1
            score = self.calculate_lifecycle_score(memory)
            
            # Semantic memories can only go to archive or be deleted
            if score < self.THRESHOLDS["semantic"]:
                if memory.success_rate < 0.5:
                    self.memory.semantic.delete(memory.id)
                    stats["deleted"] += 1
                else:
                    # Archive instead of delete if decent success rate
                    stats["archived"] += 1
        
        self._last_run = datetime.now()
        return stats
    
    def _transition(self, memory: TaskMemory, target_tier: MemoryTier, stats: dict):
        """Handle tier-specific transitions."""
        current = memory.current_tier
        
        if target_tier == MemoryTier.SEMANTIC:
            # Distill episodic to pattern
            self._distill_to_pattern(memory)
            stats["promoted"] += 1
            
        elif target_tier == MemoryTier.ARCHIVE:
            # Archive old memory
            self._archive(memory)
            stats["archived"] += 1
            
        elif target_tier.value < current.value:
            # Demoting (unusual - usually just archive)
            memory.current_tier = target_tier
            self.memory.episodic.store(memory)
            stats["demoted"] += 1
    
    def _distill_to_pattern(self, memory: TaskMemory):
        """
        Distill an episodic memory into semantic knowledge.
        Updates or creates agent capability entry.
        """
        self.memory.semantic.update_from_execution(
            agent_type=memory.agent_type,
            success=memory.outcome == "success",
            execution_time_ms=memory.execution_time_ms
        )
        
        # Add task pattern if successful
        if memory.outcome == "success":
            capability = self.memory.semantic.recall_by_agent_type(memory.agent_type)
            if capability:
                # Add refined task as a pattern (keep unique)
                pattern = memory.refined_task[:100]
                if pattern not in capability.task_patterns:
                    capability.task_patterns.append(pattern)
                    capability.task_patterns = capability.task_patterns[-10:]  # Keep last 10
                
                # Update common tools
                for tool in memory.tools_used:
                    if tool not in capability.common_tools:
                        capability.common_tools.append(tool)
                
                self.memory.semantic.store(capability)
    
    def _archive(self, memory: TaskMemory):
        """Archive a memory (compress and move to archive table)."""
        import json
        import zlib
        
        with self.memory.episodic.db.get_connection() as conn:
            # Compress memory data
            data = json.dumps({
                "raw_task": memory.raw_task,
                "refined_task": memory.refined_task,
                "agent_type": memory.agent_type,
                "outcome": memory.outcome,
                "result_summary": memory.result_summary
            }).encode()
            compressed = zlib.compress(data)
            
            # Insert into archive
            conn.execute("""
                INSERT OR REPLACE INTO archived_memories (id, original_table, compressed_data)
                VALUES (?, 'episodic_memories', ?)
            """, (memory.id, compressed))
            
            # Delete from episodic
            conn.execute("DELETE FROM episodic_memories WHERE id = ?", (memory.id,))
    
    def should_run(self, interval_minutes: int = 5) -> bool:
        """Check if lifecycle pass should run based on interval."""
        if self._last_run is None:
            return True
        return datetime.now() - self._last_run > timedelta(minutes=interval_minutes)
