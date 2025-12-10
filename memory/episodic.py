"""
Episodic Memory
===============
SQLite-backed task execution history.
"""

import json
from datetime import datetime
from typing import List, Optional
from .db import get_database
from .schemas import TaskMemory, MemoryTier
from . import embeddings


class EpisodicMemory:
    """
    Manages episodic memories (task execution history).
    Stored in encrypted SQLite.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db = get_database(db_path)
        self.db.initialize_schema()
    
    def store(self, memory: TaskMemory) -> str:
        """Store a task memory."""
        # Generate embedding if not present
        if memory.embedding is None:
            text = f"{memory.raw_task} {memory.refined_task} {memory.result_summary or ''}"
            memory.embedding = embeddings.embed(text)
        
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO episodic_memories (
                    id, created_at, last_accessed, access_count, current_tier,
                    raw_task, refined_task, task_type, agent_type, agent_image,
                    tools_used, outcome, execution_time_ms, error_message,
                    result_summary, result_data, user_feedback, user_rating, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.created_at.isoformat(),
                memory.last_accessed.isoformat(),
                memory.access_count,
                memory.current_tier.value,
                memory.raw_task,
                memory.refined_task,
                memory.task_type,
                memory.agent_type,
                memory.agent_image,
                json.dumps(memory.tools_used),
                memory.outcome,
                memory.execution_time_ms,
                memory.error_message,
                memory.result_summary,
                json.dumps(memory.result_data) if memory.result_data else None,
                memory.user_feedback,
                memory.user_rating,
                json.dumps(memory.embedding) if memory.embedding else None
            ))
        
        return memory.id
    
    def recall_by_id(self, memory_id: str) -> Optional[TaskMemory]:
        """Retrieve a specific memory by ID."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM episodic_memories WHERE id = ?",
                (memory_id,)
            ).fetchone()
        
        if row:
            memory = self._row_to_memory(row)
            self._touch(memory_id)
            return memory
        return None
    
    def recall_similar(self, query: str, limit: int = 5) -> List[TaskMemory]:
        """Retrieve memories similar to query using embeddings."""
        query_embedding = embeddings.embed(query)
        
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM episodic_memories WHERE embedding IS NOT NULL"
            ).fetchall()
        
        # Calculate similarities
        scored = []
        for row in rows:
            memory = self._row_to_memory(row)
            if memory.embedding:
                score = embeddings.similarity(query_embedding, memory.embedding)
                scored.append((score, memory))
        
        # Sort by similarity and return top matches
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [m for _, m in scored[:limit]]
        
        # Touch accessed memories
        for m in results:
            self._touch(m.id)
        
        return results
    
    def recall_by_type(self, agent_type: str, limit: int = 10) -> List[TaskMemory]:
        """Retrieve memories by agent type."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM episodic_memories WHERE agent_type = ? ORDER BY created_at DESC LIMIT ?",
                (agent_type, limit)
            ).fetchall()
        
        return [self._row_to_memory(row) for row in rows]
    
    def recall_recent(self, limit: int = 10) -> List[TaskMemory]:
        """Retrieve most recent memories."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM episodic_memories ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        
        return [self._row_to_memory(row) for row in rows]
    
    def get_all(self) -> List[TaskMemory]:
        """Get all episodic memories (for lifecycle processing)."""
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM episodic_memories").fetchall()
        return [self._row_to_memory(row) for row in rows]
    
    def delete(self, memory_id: str):
        """Delete a memory."""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM episodic_memories WHERE id = ?", (memory_id,))
    
    def _touch(self, memory_id: str):
        """Update access metadata."""
        with self.db.get_connection() as conn:
            conn.execute("""
                UPDATE episodic_memories 
                SET last_accessed = ?, access_count = access_count + 1 
                WHERE id = ?
            """, (datetime.now().isoformat(), memory_id))
    
    def _row_to_memory(self, row) -> TaskMemory:
        """Convert database row to TaskMemory object."""
        return TaskMemory(
            id=row[0],
            created_at=datetime.fromisoformat(row[1]),
            last_accessed=datetime.fromisoformat(row[2]),
            access_count=row[3],
            current_tier=MemoryTier(row[4]),
            raw_task=row[5],
            refined_task=row[6],
            task_type=row[7],
            agent_type=row[8],
            agent_image=row[9],
            tools_used=json.loads(row[10]) if row[10] else [],
            outcome=row[11],
            execution_time_ms=row[12],
            error_message=row[13],
            result_summary=row[14],
            result_data=json.loads(row[15]) if row[15] else None,
            user_feedback=row[16],
            user_rating=row[17],
            embedding=json.loads(row[18]) if row[18] else None
        )
