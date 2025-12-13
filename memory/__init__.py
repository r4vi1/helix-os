"""
Helix Memory System
===================
A three-tier memory architecture for the HelixOS Main Agent.

Memory is ONLY bound to the Main Agent - sub-agents are stateless
and receive context slices injected at spawn time.

Tiers:
- Working Memory: In-session context, 5-minute rolling buffer
- Episodic Memory: Task execution history, encrypted at rest
- Semantic Memory: Learned patterns and agent capabilities

Usage:
    from memory import MemoryManager
    
    memory = MemoryManager()
    memory.store("working", {"task": "research AI", "context": "..."})
    results = memory.recall("AI research", limit=5)
"""

from .manager import MemoryManager
from .schemas import TaskMemory, AgentCapability, MemoryEntry
from .context_slicer import ContextSlicer
from .lifecycle_controller import MemoryLifecycleController

__all__ = [
    "MemoryManager",
    "TaskMemory",
    "AgentCapability",
    "MemoryEntry",
    "ContextSlicer",
    "MemoryLifecycleController",
]

__version__ = "0.1.0"
