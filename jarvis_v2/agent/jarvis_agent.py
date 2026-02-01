"""
Simple Agent wrapper
Will be expanded to use LangGraph/LangChain
"""

from typing import AsyncGenerator, List, Dict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from jarvis_assistant.core.agent import get_agent
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import AgentConfig

class JarvisAgent:
    """
    AI Agent for Jarvis.
    Uses existing agent implementation with cleaner interface.
    
    Usage:
        agent = JarvisAgent()
        
        async for response in agent.respond("What's the weather?"):
            print(response)
    """
    
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        
        print("Initializing Jarvis Agent...")
        
        # Use existing agent
        try:
            self.brain = get_agent()
            print("✅ Agent initialized")
        except Exception as e:
            print(f"⚠️ Failed to initialize agent: {e}")
            self.brain = None
        
        # Conversation history
        self.history: List[Dict[str, str]] = []
    
    async def respond(
        self,
        user_input: str
    ) -> AsyncGenerator[str, None]:
        """
        Generate response to user input.
        
        Args:
            user_input: User's text input
            
        Yields:
            str: Response chunks (for streaming TTS)
        """
        if not self.brain:
            yield "抱歉，大脑还没准备好。"
            return
        
        # Add to history
        self.history.append({"role": "user", "content": user_input})
        
        try:
            # Use existing agent
            result = await self.brain.process(user_input)
            
            # Add to history
            self.history.append({"role": "assistant", "content": result})
            
            # Yield response (can be split for streaming)
            yield result
            
        except Exception as e:
            error_msg = f"抱歉，出了点问题：{str(e)}"
            print(f"❌ Agent error: {e}")
            yield error_msg
    
    def clear_history(self):
        """Clear conversation history"""
        self.history = []
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.history.copy()
