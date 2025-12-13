"""
Context Slicer
==============
Extracts relevant context subset for sub-agent injection.
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import MemoryManager


class ContextSlicer:
    """
    Extracts relevant context from main agent memory for sub-agent injection.
    Sub-agents don't get full memory - only what they need.
    """
    
    def __init__(self, memory_manager: "MemoryManager"):
        self.memory = memory_manager
    
    def slice_for_task(self, task_spec: str, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract minimal relevant context for a sub-agent.
        
        Args:
            task_spec: The refined task specification
            agent_type: Optional agent type to filter relevant history
            
        Returns:
            Context dict to inject into sub-agent prompt
        """
        context = {
            "similar_tasks": [],
            "relevant_patterns": [],
            "user_preferences": {},
            "suggested_tools": []
        }
        
        # 1. Get similar past tasks from episodic memory
        similar = self.memory.recall(task_spec, memory_type="episodic", limit=3)
        for task in similar:
            if hasattr(task, 'result_summary') and task.outcome == "success":
                context["similar_tasks"].append({
                    "task": task.refined_task,
                    "approach": task.result_summary,
                    "tools_used": task.tools_used
                })
        
        # 2. Get relevant patterns from semantic memory
        patterns = self.memory.recall(task_spec, memory_type="semantic", limit=2)
        for pattern in patterns:
            if hasattr(pattern, 'task_patterns'):
                context["relevant_patterns"].extend(pattern.task_patterns[:3])
                context["suggested_tools"].extend(pattern.common_tools[:3])
        
        # 3. Get agent-specific capability if known
        if agent_type:
            capability = self.memory.semantic.recall_by_agent_type(agent_type)
            if capability:
                context["agent_capability"] = {
                    "success_rate": capability.success_rate,
                    "avg_time_ms": capability.avg_execution_time_ms,
                    "common_tools": capability.common_tools
                }
        
        # 4. Get relevant working memory context
        working_ctx = self.memory.working.get_full_context()
        if working_ctx.get("conversation_history"):
            # Only include last 2 relevant exchanges
            context["recent_conversation"] = working_ctx["conversation_history"][-2:]
        
        # Deduplicate suggested tools
        context["suggested_tools"] = list(set(context["suggested_tools"]))
        
        return context
    
    def format_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format context dict as a prompt section for injection.
        """
        lines = ["## Context from Previous Experience\n"]
        
        if context.get("similar_tasks"):
            lines.append("### Similar Past Tasks:")
            for task in context["similar_tasks"]:
                lines.append(f"- Task: {task['task'][:100]}...")
                if task.get("approach"):
                    lines.append(f"  Approach: {task['approach'][:100]}...")
            lines.append("")
        
        if context.get("relevant_patterns"):
            lines.append("### Known Patterns:")
            for pattern in context["relevant_patterns"][:3]:
                lines.append(f"- {pattern}")
            lines.append("")
        
        if context.get("suggested_tools"):
            lines.append(f"### Suggested Tools: {', '.join(context['suggested_tools'][:5])}")
            lines.append("")
        
        if context.get("agent_capability"):
            cap = context["agent_capability"]
            lines.append(f"### Agent Stats: {cap['success_rate']*100:.0f}% success rate, avg {cap['avg_time_ms']:.0f}ms")
            lines.append("")
        
        return "\n".join(lines) if len(lines) > 1 else ""
