"""
Memory Module Tests
===================
Basic tests for the memory system.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
import tempfile


def test_memory_basic():
    """Test basic memory operations."""
    from memory import MemoryManager
    from memory.schemas import TaskMemory
    
    # Use temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        memory = MemoryManager(db_path=db_path)
        
        # Test start/complete task
        task = memory.start_task(
            raw_task="calculate fibonacci 10",
            refined_task="Calculate the 10th Fibonacci number",
            agent_type="compute_agent"
        )
        assert task is not None
        assert memory.working.get_current_task() is not None
        
        # Complete task
        memory_id = memory.complete_task(
            outcome="success",
            result_summary="Fibonacci(10) = 55",
            execution_time_ms=150
        )
        assert memory_id is not None
        assert memory.working.get_current_task() is None
        
        # Recall from episodic
        results = memory.recall("fibonacci", memory_type="episodic")
        assert len(results) > 0
        assert "fibonacci" in results[0].refined_task.lower()
        
        print("✓ Basic memory operations work!")
        
    finally:
        os.unlink(db_path)


def test_context_slicer():
    """Test context slicing for sub-agents."""
    from memory import MemoryManager
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        memory = MemoryManager(db_path=db_path)
        
        # Create some history
        for i in range(3):
            memory.start_task(f"research task {i}", agent_type="research_agent")
            memory.complete_task(outcome="success", result_summary=f"Found info {i}")
        
        # Get context for new similar task
        context = memory.get_context_for_subagent("research new topic")
        
        assert "similar_tasks" in context
        print(f"✓ Context slicer returned {len(context['similar_tasks'])} similar tasks")
        
    finally:
        os.unlink(db_path)


def test_working_memory():
    """Test working memory operations."""
    from memory.working import WorkingMemory
    
    wm = WorkingMemory(buffer_minutes=5)
    
    # Test passive buffer
    wm.add_to_passive_buffer("hello world")
    wm.add_to_passive_buffer("test transcription")
    
    buffer = wm.get_passive_buffer()
    assert "hello world" in buffer
    assert "test transcription" in buffer
    
    # Test conversation history
    wm.add_conversation("user", "What is AI?")
    wm.add_conversation("assistant", "AI is...")
    
    history = wm.get_conversation_history()
    assert len(history) == 2
    
    print("✓ Working memory operations work!")


def test_embeddings():
    """Test embedding generation."""
    from memory import embeddings
    
    # Test embedding
    emb1 = embeddings.embed("hello world")
    emb2 = embeddings.embed("hello world")
    emb3 = embeddings.embed("completely different text")
    
    assert len(emb1) > 0
    
    # Same text should have same embedding
    sim_same = embeddings.similarity(emb1, emb2)
    assert sim_same > 0.99
    
    # Different text should have lower similarity
    sim_diff = embeddings.similarity(emb1, emb3)
    assert sim_diff < sim_same
    
    print("✓ Embeddings work!")


def test_lifecycle():
    """Test lifecycle scoring."""
    from memory import MemoryManager
    from memory.schemas import TaskMemory, MemoryTier
    from datetime import timedelta
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        memory = MemoryManager(db_path=db_path)
        
        # Create a recent memory
        task = TaskMemory(
            raw_task="recent task",
            refined_task="A very recent task",
            agent_type="test_agent",
            outcome="success"
        )
        memory.episodic.store(task)
        
        # Create an old memory
        old_task = TaskMemory(
            raw_task="old task",
            refined_task="An old task from long ago",
            agent_type="test_agent",
            outcome="failure"
        )
        old_task.last_accessed = datetime.now() - timedelta(days=60)
        memory.episodic.store(old_task)
        
        # Test scoring
        recent = memory.episodic.recall_by_id(task.id)
        old = memory.episodic.recall_by_id(old_task.id)
        
        recent_score = memory.lifecycle.calculate_lifecycle_score(recent)
        old_score = memory.lifecycle.calculate_lifecycle_score(old)
        
        assert recent_score > old_score, "Recent memory should have higher score"
        print(f"✓ Lifecycle scoring: recent={recent_score:.2f}, old={old_score:.2f}")
        
    finally:
        os.unlink(db_path)


if __name__ == "__main__":
    print("Running memory tests...\n")
    
    test_embeddings()
    test_working_memory()
    test_memory_basic()
    test_context_slicer()
    test_lifecycle()
    
    print("\n✅ All tests passed!")
