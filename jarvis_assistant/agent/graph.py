"""
LangGraph state machine for Jarvis agent.
Defines workflow as a graph: nodes (steps) + edges (transitions).
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import JarvisState
from .nodes import planner_node, executor_node, synthesizer_node, should_continue


def create_jarvis_graph():
    """
    Create LangGraph state machine for Jarvis.
    
    Workflow:
        1. Planner → Create execution plan
        2. Executor → Execute each step (loops)
        3. Synthesizer → Combine results into final response
    
    Returns:
        Compiled LangGraph application with checkpointing
    """
    # Create graph with state schema
    workflow = StateGraph(JarvisState)
    
    # Add nodes (steps in workflow)
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    # Define edges (transitions between nodes)
    
    # Start at planner
    workflow.set_entry_point("planner")
    
    # Planner → Executor (always)
    workflow.add_edge("planner", "executor")
    
    # Executor → Executor OR Synthesizer (conditional)
    workflow.add_conditional_edges(
        "executor",
        should_continue,  # Routing function
        {
            "executor": "executor",          # Loop: More steps
            "synthesizer": "synthesizer",    # Done: Synthesize
        }
    )
    
    # Synthesizer → END (done)
    workflow.add_edge("synthesizer", END)
    
    # Compile with in-memory checkpointing
    # TODO: Replace with SqliteSaver for persistence
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    return app
