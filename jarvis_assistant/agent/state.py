"""
State definition for Jarvis agent using LangGraph.
This is the agent's "memory" that persists across conversation turns.
"""

from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph.message import add_messages


class JarvisState(TypedDict):
    """
    Agent state - persisted across entire conversation.
    
    LangGraph automatically manages state updates using reducer functions.
    Each node returns partial state updates that get merged into full state.
    """
    
    # === Conversation Context ===
    messages: Annotated[List[Dict], add_messages]
    """Message history (LangGraph format). Reducer: add_messages (append new)."""
    
    user_input: str
    """Current user query text."""
    
    agent_response: str
    """Final agent response text."""
    
    # === Planning & Execution ===
    plan: Optional[Dict]
    """
    Execution plan from planner node.
    Structure: {"steps": [{"name": str, "tool_name": str, "tool_args": dict, "description": str}]}
    """
    
    current_step: int
    """Current step index in plan (0-indexed)."""
    
    # === User Context (from memory.json) ===
    user_profile: Dict
    """User background, preferences, projects from memory system."""
    
    conversation_history: List[Dict]
    """Recent conversation context (last N turns)."""
    
    # === Tool Execution ===
    tool_results: Dict[str, str]
    """Mapping of step_name → tool_result. Accumulated during execution."""
    
    tools_used: List[str]
    """List of tool names used in this query. For logging/analytics."""
    
    # === Metadata ===
    session_id: str
    """Session identifier for checkpointing."""
    
    timestamp: str
    """Query timestamp."""
    
    # === Optional Flags ===
    needs_synthesis: bool
    """Flag: True if tool results need natural language synthesis."""
    
    error: Optional[str]
    """Error message if something failed."""
