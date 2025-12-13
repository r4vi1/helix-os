"""
Memory Schemas
==============
Dataclass definitions for memory entries across all tiers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Literal, Dict, Any
from enum import Enum
import uuid


class MemoryTier(Enum):
    """Memory tier classification."""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    ARCHIVE = "archive"


@dataclass
class MemoryEntry:
    """
    Base class for all memory entries.
    Tracks metadata for lifecycle management.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    current_tier: MemoryTier = MemoryTier.WORKING
    
    # Embedding for semantic search (populated lazily)
    embedding: Optional[List[float]] = None
    
    def touch(self):
        """Update access metadata."""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class TaskMemory(MemoryEntry):
    """
    Episodic memory of a task execution.
    Stores what happened, outcome, and learnings.
    """
    # Task details
    raw_task: str = ""
    refined_task: str = ""
    task_type: str = ""  # research, compute, synthesis, etc.
    
    # Agent details
    agent_type: str = ""
    agent_image: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)
    
    # Execution details
    outcome: Literal["success", "failure", "partial", "pending"] = "pending"
    execution_time_ms: int = 0
    error_message: Optional[str] = None
    
    # Results
    result_summary: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    
    # User feedback for learning
    user_feedback: Optional[str] = None
    user_rating: Optional[int] = None  # 1-5 scale
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (1.0 for success, 0.0 for failure)."""
        if self.outcome == "success":
            return 1.0
        elif self.outcome == "partial":
            return 0.5
        return 0.0


@dataclass
class AgentCapability(MemoryEntry):
    """
    Semantic memory of learned agent capabilities.
    Distilled from multiple episodic memories.
    """
    # Capability description
    agent_type: str = ""
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    
    # Performance metrics (aggregated)
    total_executions: int = 0
    successful_executions: int = 0
    avg_execution_time_ms: float = 0.0
    
    # Tools and patterns
    common_tools: List[str] = field(default_factory=list)
    task_patterns: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate aggregate success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions


@dataclass
class WorkingContext:
    """
    Working memory context for current session.
    Includes rolling buffer for passive mode.
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.now)
    
    # Current task being worked on
    current_task: Optional[TaskMemory] = None
    
    # Conversation history (last N exchanges)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    
    # Passive mode rolling buffer (transcriptions)
    passive_buffer: List[Dict[str, Any]] = field(default_factory=list)
    passive_buffer_max_minutes: int = 5
    
    # Active context variables
    context_variables: Dict[str, Any] = field(default_factory=dict)
    
    def add_to_buffer(self, transcription: str, timestamp: Optional[datetime] = None):
        """Add transcription to passive buffer with automatic cleanup."""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.passive_buffer.append({
            "text": transcription,
            "timestamp": timestamp
        })
        
        # Cleanup old entries
        self._cleanup_buffer()
    
    def _cleanup_buffer(self):
        """Remove entries older than buffer_max_minutes."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(minutes=self.passive_buffer_max_minutes)
        self.passive_buffer = [
            entry for entry in self.passive_buffer
            if entry["timestamp"] > cutoff
        ]
    
    def get_buffer_text(self) -> str:
        """Get all buffer text concatenated."""
        return " ".join(entry["text"] for entry in self.passive_buffer)


@dataclass
class UserPreference(MemoryEntry):
    """
    Learned user preferences from corrections and feedback.
    """
    preference_type: str = ""  # output_format, verbosity, etc.
    preference_value: str = ""
    confidence: float = 0.5  # How confident we are in this preference
    source_task_ids: List[str] = field(default_factory=list)
