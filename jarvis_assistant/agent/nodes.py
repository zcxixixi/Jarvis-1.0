"""
Agent nodes - individual steps in the LangGraph workflow.
Each node takes state as input, performs work, returns state updates.
"""

from typing import Dict, Any
from .state import JarvisState

# TODO: These will import from existing agent.py logic
# from jarvis_assistant.core.agent import JarvisAgent as LegacyAgent


async def planner_node(state: JarvisState) -> Dict[str, Any]:
    """
    Node 1: Create execution plan using Doubao LLM.
    
    Input state:
        - user_input: User query
        - user_profile: User context
        - conversation_history: Recent messages
    
    Returns state updates:
        - plan: Execution plan with steps
        - current_step: 0 (reset to start)
        - needs_synthesis: True if multiple tools used
    """
    # TODO: Extract planning logic from jarvis_assistant/core/agent.py
    # For now, return dummy plan
    
    user_input = state["user_input"]
    
    # Dummy plan (will be replaced with real Doubao planner)
    plan = {
        "steps": [
            {
                "name": "respond",
                "tool_name": None,  # Conversational response
                "tool_args": {},
                "description": f"Respond to: {user_input}"
            }
        ]
    }
    
    return {
        "plan": plan,
        "current_step": 0,
        "needs_synthesis": len(plan["steps"]) > 1,
    }


async def executor_node(state: JarvisState) -> Dict[str, Any]:
    """
    Node 2: Execute one step from the plan.
    
    Input state:
        - plan: Execution plan
        - current_step: Which step to execute
        - tool_results: Accumulated results
    
    Returns state updates:
        - tool_results: Updated with new result
        - tools_used: Append tool name
        - current_step: Increment by 1
    """
    # TODO: Extract execution logic from jarvis_assistant/core/agent.py
    
    plan = state["plan"]
    step_idx = state["current_step"]
    step = plan["steps"][step_idx]
    
    # Execute step
    if step["tool_name"]:
        # TODO: Call actual tool
        result = f"[Tool {step['tool_name']} executed]"
    else:
        # TODO: Generate conversational response
        result = f"I understand you asked: {state['user_input']}"
    
    # Update state
    return {
        "tool_results": {**state.get("tool_results", {}), step["name"]: result},
        "tools_used": state.get("tools_used", []) + ([step["tool_name"]] if step["tool_name"] else []),
        "current_step": step_idx + 1,
    }


async def synthesizer_node(state: JarvisState) -> Dict[str, Any]:
    """
    Node 3: Synthesize final response from tool results.
    
    Input state:
        - tool_results: All tool results
        - needs_synthesis: Whether to synthesize or return raw
        - user_input: Original query (for context)
    
    Returns state updates:
        - agent_response: Final natural language response
    """
    # TODO: Extract synthesis logic from jarvis_assistant/core/agent.py
    
    results = state.get("tool_results", {})
    
    if state.get("needs_synthesis") and len(results) > 1:
        # Multiple results, synthesize into coherent response
        # TODO: Use Doubao to synthesize
        response = "I completed multiple tasks:\n" + "\n".join(
            f"- {name}: {result}" for name, result in results.items()
        )
    else:
        # Single result or no synthesis needed
        response = list(results.values())[0] if results else "I'm ready to help."
    
    return {
        "agent_response": response,
    }


def should_continue(state: JarvisState) -> str:
    """
    Routing function: Decide next node after executor.
    
    Returns:
        - "executor": More steps to execute
        - "synthesizer": Done executing, synthesize response
    """
    plan = state["plan"]
    current_step = state["current_step"]
    
    if current_step < len(plan["steps"]):
        return "executor"  # More steps
    else:
        return "synthesizer"  # Done
