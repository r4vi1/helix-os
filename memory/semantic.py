"""
Semantic Memory
===============
Learned patterns and agent capabilities.
"""

import json
from datetime import datetime
from typing import List, Optional
from .db import get_database
from .schemas import AgentCapability, MemoryTier
from . import embeddings


class SemanticMemory:
    """
    Manages semantic memories (learned agent capabilities and patterns).
    Distilled from multiple episodic memories.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db = get_database(db_path)
        self.db.initialize_schema()
    
    def store(self, capability: AgentCapability) -> str:
        """Store or update an agent capability."""
        # Generate embedding
        if capability.embedding is None:
            text = f"{capability.agent_type} {capability.description} {' '.join(capability.keywords)}"
            capability.embedding = embeddings.embed(text)
        
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO semantic_memories (
                    id, created_at, last_accessed, access_count, current_tier,
                    agent_type, description, keywords, total_executions,
                    successful_executions, avg_execution_time_ms, common_tools,
                    task_patterns, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                capability.id,
                capability.created_at.isoformat(),
                capability.last_accessed.isoformat(),
                capability.access_count,
                capability.current_tier.value,
                capability.agent_type,
                capability.description,
                json.dumps(capability.keywords),
                capability.total_executions,
                capability.successful_executions,
                capability.avg_execution_time_ms,
                json.dumps(capability.common_tools),
                json.dumps(capability.task_patterns),
                json.dumps(capability.embedding) if capability.embedding else None
            ))
        
        return capability.id
    
    def recall_by_agent_type(self, agent_type: str) -> Optional[AgentCapability]:
        """Get capability for a specific agent type."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM semantic_memories WHERE agent_type = ?",
                (agent_type,)
            ).fetchone()
        
        if row:
            return self._row_to_capability(row)
        return None
    
    def recall_similar(self, query: str, limit: int = 3) -> List[AgentCapability]:
        """Find capabilities similar to query."""
        query_embedding = embeddings.embed(query)
        
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM semantic_memories WHERE embedding IS NOT NULL"
            ).fetchall()
        
        scored = []
        for row in rows:
            cap = self._row_to_capability(row)
            if cap.embedding:
                score = embeddings.similarity(query_embedding, cap.embedding)
                scored.append((score, cap))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:limit]]
    
    def get_all(self) -> List[AgentCapability]:
        """Get all semantic memories."""
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM semantic_memories").fetchall()
        return [self._row_to_capability(row) for row in rows]
    
    def update_from_execution(self, agent_type: str, success: bool, execution_time_ms: int):
        """Update capability stats from a new execution."""
        existing = self.recall_by_agent_type(agent_type)
        
        if existing:
            existing.total_executions += 1
            if success:
                existing.successful_executions += 1
            # Running average of execution time
            existing.avg_execution_time_ms = (
                (existing.avg_execution_time_ms * (existing.total_executions - 1) + execution_time_ms)
                / existing.total_executions
            )
            self.store(existing)
        else:
            # Create new capability entry
            cap = AgentCapability(
                agent_type=agent_type,
                description=f"Auto-learned capability for {agent_type}",
                total_executions=1,
                successful_executions=1 if success else 0,
                avg_execution_time_ms=float(execution_time_ms),
                current_tier=MemoryTier.SEMANTIC
            )
            self.store(cap)
    
    def delete(self, capability_id: str):
        """Delete a capability."""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM semantic_memories WHERE id = ?", (capability_id,))
    
    def _row_to_capability(self, row) -> AgentCapability:
        """Convert database row to AgentCapability."""
        return AgentCapability(
            id=row[0],
            created_at=datetime.fromisoformat(row[1]),
            last_accessed=datetime.fromisoformat(row[2]),
            access_count=row[3],
            current_tier=MemoryTier(row[4]),
            agent_type=row[5],
            description=row[6],
            keywords=json.loads(row[7]) if row[7] else [],
            total_executions=row[8],
            successful_executions=row[9],
            avg_execution_time_ms=row[10],
            common_tools=json.loads(row[11]) if row[11] else [],
            task_patterns=json.loads(row[12]) if row[12] else [],
            embedding=json.loads(row[13]) if row[13] else None
        )
