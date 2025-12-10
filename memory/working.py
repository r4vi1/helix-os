"""
Working Memory
==============
In-session context including passive mode rolling buffer.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from .schemas import WorkingContext, TaskMemory


class WorkingMemory:
    """
    Manages in-session working memory.
    This is RAM-only, not persisted to disk.
    """
    
    def __init__(self, buffer_minutes: int = 5):
        self.context = WorkingContext(passive_buffer_max_minutes=buffer_minutes)
        self._temp_storage: Dict[str, Any] = {}
    
    def set_current_task(self, task: TaskMemory):
        """Set the currently active task."""
        self.context.current_task = task
    
    def get_current_task(self) -> Optional[TaskMemory]:
        """Get the currently active task."""
        return self.context.current_task
    
    def clear_current_task(self) -> Optional[TaskMemory]:
        """Clear and return the current task (for promotion to episodic)."""
        task = self.context.current_task
        self.context.current_task = None
        return task
    
    def add_conversation(self, role: str, content: str):
        """Add to conversation history."""
        self.context.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # Keep last 20 exchanges
        if len(self.context.conversation_history) > 20:
            self.context.conversation_history = self.context.conversation_history[-20:]
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history."""
        return self.context.conversation_history[-limit:]
    
    def add_to_passive_buffer(self, transcription: str):
        """Add transcription to passive mode buffer."""
        self.context.add_to_buffer(transcription)
    
    def get_passive_buffer(self) -> str:
        """Get concatenated passive buffer text."""
        return self.context.get_buffer_text()
    
    def set_variable(self, key: str, value: Any):
        """Set a context variable."""
        self.context.context_variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.context.context_variables.get(key, default)
    
    def store(self, key: str, data: Any):
        """Store temporary data."""
        self._temp_storage[key] = data
    
    def recall(self, key: str) -> Optional[Any]:
        """Recall temporary data."""
        return self._temp_storage.get(key)
    
    def get_full_context(self) -> Dict[str, Any]:
        """Get complete working memory state for context injection."""
        return {
            "session_id": self.context.session_id,
            "current_task": self.context.current_task,
            "conversation_history": self.context.conversation_history[-5:],
            "passive_buffer": self.get_passive_buffer(),
            "variables": self.context.context_variables
        }
    
    def clear(self):
        """Clear all working memory (end of session)."""
        self.context = WorkingContext(
            passive_buffer_max_minutes=self.context.passive_buffer_max_minutes
        )
        self._temp_storage.clear()
