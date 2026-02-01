"""
Jarvis Agent - Pure text-in, text-out agent (no I/O dependencies).
Uses LangGraph for stateful workflow management.
Optimized for <1s first token latency (voice UX critical).
"""

from datetime import datetime
from typing import AsyncIterator
import re
from .graph import create_jarvis_graph
from .state import JarvisState


class JarvisAgent:
    """
    Pure agent - no ASR/TTS knowledge.
    Processes text input and returns text output.
    
    CRITICAL: Optimized for <1s first token latency!
    - Streaming support for real-time output
    - Fast-path for simple queries (skip planning)
    - Immediate response generation
    
    This is the "brain" - it should never know about:
    - Audio input (ASR)
    - Audio output (TTS)
    - Websockets, APIs, etc.
    
    The orchestrator handles all I/O.
    """
    
    # Simple query patterns (fast-path, no tools needed)
    SIMPLE_PATTERNS = [
        r'^(hi|hello|hey|你好|嗨|哈喽)\s*[!.。]*$',
        r'^(thanks?|thank you|谢谢|多谢)\s*[!.。]*$',
        r'^(bye|goodbye|再见|拜拜)\s*[!.。]*$',
        r'^(yes|no|ok|okay|好|不)\s*[!.。]*$',
        r'^(how are you|你好吗|怎么样)\s*[?？]*$',
    ]
    
    def __init__(self, session_id: str = "default", enable_streaming: bool = True):
        """
        Initialize agent with LangGraph state machine.
        
        Args:
            session_id: Session identifier for checkpointing (multi-user support)
            enable_streaming: Enable streaming for <1s latency (default: True)
        """
        self.graph = create_jarvis_graph()
        self.session_id = session_id
        self.enable_streaming = enable_streaming
    
    def _is_simple_query(self, text: str) -> bool:
        """
        Detect if query is simple (fast-path, no tools needed).
        
        Simple queries:
        - Greetings: "hello", "你好"
        - Thank you: "thanks", "谢谢"
        - Short responses: "yes", "no", "ok"
        - Very short (<5 words)
        
        Args:
            text: User input text
            
        Returns:
            True if simple query (use fast-path)
        """
        text_lower = text.lower().strip()
        
        # Pattern matching
        for pattern in self.SIMPLE_PATTERNS:
            if re.match(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Length heuristic (very short = likely simple)
        word_count = len(text.split())
        if word_count <= 3:
            return True
        
        return False
    
    async def process(self, text: str) -> str:
        """
        Process user input and return agent response.
        
        Pure text → text transformation.
        All state management handled by LangGraph.
        
        Args:
            text: User input text
            
        Returns:
            str: Agent response text
        """
        # Initial state
        initial_state: JarvisState = {
            "user_input": text,
            "agent_response": "",
            "messages": [],
            "plan": None,
            "current_step": 0,
            "user_profile": {},  # TODO: Load from memory
            "conversation_history": [],  # TODO: Load from memory
            "tool_results": {},
            "tools_used": [],
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "needs_synthesis": False,
            "error": None,
        }
        
        # Run graph with checkpointing
        config = {"configurable": {"thread_id": self.session_id}}
        
        try:
            final_state = await self.graph.ainvoke(initial_state, config)
            return final_state["agent_response"]
        except Exception as e:
            # Graceful error handling
            return f"Sorry, I encountered an error: {str(e)}"
    
    async def process_stream(self, text: str) -> AsyncIterator[str]:
        """
        🚀 STREAMING: Process input and yield response chunks in real-time.
        
        CRITICAL for voice UX: First chunk must be <1s!
        
        Strategy:
        1. Fast-path detection (skip planning for simple queries)
        2. Stream LLM responses directly
        3. Yield chunks as they arrive
        
        Args:
            text: User input text
            
        Yields:
            str: Response chunks in real-time
        """
        # Import LLM client
        from .llm_client import DoubaoLLMClient
        
        llm = DoubaoLLMClient()
        
        # Fast-path for simple queries
        if self._is_simple_query(text):
            # 🚀 REAL Doubao streaming (500-700ms first token)
            async for chunk in llm.generate_stream(
                user_message=text,
                system_prompt="You are Jarvis, a helpful voice assistant. Be concise and natural.",
                temperature=0.7
            ):
                yield chunk
        
        else:
            # Complex queries: Full LangGraph workflow
            # For now, use streaming LLM directly (TODO: make LangGraph streaming)
            async for chunk in llm.generate_stream(
                user_message=text,
                system_prompt="You are Jarvis, a helpful voice assistant.",
                temperature=0.7
            ):
                yield chunk
    
    def get_state_history(self):
        """
        Get conversation state history (for debugging/analytics).
        
        Returns:
            List of state snapshots from checkpointer
        """
        # TODO: Query checkpointer for history
        pass
