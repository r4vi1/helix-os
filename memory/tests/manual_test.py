#!/usr/bin/env python3
"""
HelixOS Memory System - Manual Testing Guide
=============================================
Run this script and follow the prompts to test memory features.

Usage:
    source venv/bin/activate
    python3 memory/tests/manual_test.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from memory import MemoryManager

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def pause():
    input("\n👉 Press Enter to continue...")

def main():
    print_header("🧠 HelixOS Memory System - Manual Testing")
    
    # Initialize
    print("Initializing memory system...")
    memory = MemoryManager()
    print("✅ Memory system ready!\n")
    
    # =========================================
    # TEST 1: Remember a task
    # =========================================
    print_header("TEST 1: Can it remember what I asked it to do?")
    
    print("Scenario: You ask HelixOS to research something.\n")
    
    task_request = input("Type a task (or press Enter for default): ").strip()
    if not task_request:
        task_request = "research the history of artificial intelligence"
    
    print(f"\n📝 You asked: '{task_request}'")
    
    # Simulate the task flow
    task = memory.start_task(
        raw_task=task_request,
        refined_task=f"Research and summarize: {task_request}",
        agent_type="research_agent"
    )
    print(f"📌 Task started and stored in working memory")
    
    # Complete it
    memory.complete_task(
        outcome="success",
        result_summary=f"Successfully researched: {task_request}",
        execution_time_ms=3500
    )
    print(f"✅ Task completed and moved to episodic memory (long-term)")
    
    pause()
    
    # =========================================
    # TEST 2: Recall past tasks
    # =========================================
    print_header("TEST 2: Can it recall what I asked before?")
    
    print("Scenario: You ask something similar, does it remember?\n")
    
    search_query = input("Search for a past task (or press Enter for 'AI'): ").strip()
    if not search_query:
        search_query = "AI"
    
    # Only search episodic memory (task history)
    results = memory.recall(search_query, memory_type="episodic", limit=5)
    
    if results:
        print(f"\n🔍 Found {len(results)} related memories:\n")
        for i, r in enumerate(results, 1):
            print(f"  {i}. Task: {r.raw_task}")
            print(f"     Result: {r.result_summary}")
            print(f"     Outcome: {r.outcome}")
            print()
    else:
        print("❌ No memories found. Try adding more tasks first!")
    
    pause()
    
    # =========================================
    # TEST 3: Learning patterns
    # =========================================
    print_header("TEST 3: Does it learn patterns over time?")
    
    print("Scenario: After doing many similar tasks, it should learn.\n")
    print("Let's simulate 5 research tasks...\n")
    
    topics = ["machine learning", "neural networks", "deep learning", "transformers", "GPT"]
    for topic in topics:
        memory.start_task(f"research {topic}", agent_type="research_agent")
        memory.complete_task(outcome="success", result_summary=f"Explained {topic}")
        print(f"  ✅ Completed: research {topic}")
    
    print("\n📊 What has it learned about research_agent?\n")
    
    cap = memory.semantic.recall_by_agent_type("research_agent")
    if cap:
        print(f"  Agent Type: {cap.agent_type}")
        print(f"  Total Tasks: {cap.total_executions}")
        print(f"  Success Rate: {cap.success_rate:.0%}")
        print(f"  Avg Time: {cap.avg_execution_time_ms:.0f}ms")
    
    pause()
    
    # =========================================
    # TEST 4: Context for new tasks
    # =========================================
    print_header("TEST 4: Does it help with new similar tasks?")
    
    print("Scenario: You ask to research something new. Does it use past experience?\n")
    
    new_task = input("Enter a new task (or press Enter for 'research BERT model'): ").strip()
    if not new_task:
        new_task = "research BERT model"
    
    context = memory.get_context_for_subagent(new_task, "research_agent")
    
    print(f"\n🧠 Context it would give to a sub-agent for '{new_task}':\n")
    
    if context["similar_tasks"]:
        print("  📚 Similar past tasks:")
        for t in context["similar_tasks"][:3]:
            print(f"    - {t['task'][:60]}...")
    
    if context.get("agent_capability"):
        cap = context["agent_capability"]
        print(f"\n  📊 Agent stats: {cap['success_rate']*100:.0f}% success rate")
    
    pause()
    
    # =========================================
    # TEST 5: Passive listening buffer
    # =========================================
    print_header("TEST 5: Does it remember background conversations?")
    
    print("Scenario: In passive mode, it listens and remembers context.\n")
    
    print("Simulating overheard phrases...")
    memory.add_passive_transcription("I prefer bullet points over paragraphs")
    memory.add_passive_transcription("I usually work on Python projects")
    memory.add_passive_transcription("Keep explanations short please")
    
    print("\n🎤 Passive buffer contents:")
    print(f"  '{memory.get_passive_buffer()}'\n")
    
    print("This context would be available when you give a command!")
    
    pause()
    
    # =========================================
    # TEST 6: Data persists
    # =========================================
    print_header("TEST 6: Does data survive restarts?")
    
    print("All your data is saved to: ~/.helix/memory.db\n")
    
    stats = memory.get_stats()
    print(f"📊 Current memory stats:")
    print(f"  - Episodic memories (task history): {stats['episodic_count']}")
    print(f"  - Semantic memories (learned patterns): {stats['semantic_count']}")
    print(f"  - Active task in working memory: {stats['working_has_task']}")
    
    print("\n💡 Tip: Exit Python and run this script again.")
    print("   Your memories will still be there!")
    
    pause()
    
    # =========================================
    # Summary
    # =========================================
    print_header("✅ Testing Complete!")
    
    print("What you tested:")
    print("  1. ✅ Memory stores tasks you give it")
    print("  2. ✅ Memory recalls similar past tasks")
    print("  3. ✅ Memory learns patterns (success rates, common tasks)")
    print("  4. ✅ Memory provides context for new sub-agents")
    print("  5. ✅ Passive buffer remembers background context")
    print("  6. ✅ Data persists in ~/.helix/memory.db")
    
    print("\n🎯 Real-world impact:")
    print("  - Second time you ask 'research X', it remembers past research")
    print("  - Failing tasks get lower priority, successful ones get reused")
    print("  - Sub-agents get hints from past experiences")
    print("  - You don't repeat yourself - it remembers preferences")
    
    print("\n")

if __name__ == "__main__":
    main()
