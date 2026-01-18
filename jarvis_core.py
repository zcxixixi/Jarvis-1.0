"""
JARVIS Core AI Engine
Handles conversation and AI interactions
"""
import json
from typing import List, Dict, Optional
from openai import OpenAI
from config import Config

class JarvisCore:
    """JARVIS AI Engine"""
    
    def __init__(self):
        """Initialize JARVIS"""
        if Config.LLM_PROVIDER == "groq":
            self.client = OpenAI(
                api_key=Config.GROQ_API_KEY,
                base_url=Config.GROQ_API_BASE
            )
            self.model = Config.GROQ_MODEL
        elif Config.LLM_PROVIDER == "ollama":
            self.client = OpenAI(
                api_key="ollama",
                base_url=Config.OLLAMA_BASE_URL
            )
            self.model = Config.OLLAMA_MODEL
        else:  # grok
            self.client = OpenAI(
                api_key=Config.GROK_API_KEY,
                base_url=Config.GROK_API_BASE
            )
            self.model = Config.GROK_MODEL
        self.conversation_history: List[Dict] = []
        self.tools = []  # Will be populated with available tools
        
        # Initialize conversation with system prompt
        self.conversation_history.append({
            "role": "system",
            "content": Config.SYSTEM_PROMPT
        })
    
    def chat(self, user_message: str) -> str:
        """
        Send a message to JARVIS and get response
        
        Args:
            user_message: User's message
            
        Returns:
            JARVIS's response
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Trim history if too long
        self._trim_history()
        
        try:
            # Call LLM API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS,
                tools=self.tools if self.tools else None
            )
            
            # Extract response
            assistant_message = response.choices[0].message
            
            # Handle tool calls if present
            if assistant_message.tool_calls:
                return self._handle_tool_calls(assistant_message)
            
            # Get text response
            reply = assistant_message.content
            
            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": reply
            })
            
            return reply
            
        except Exception as e:
            error_msg = f"抱歉，我遇到了一个问题: {str(e)}"
            if Config.DEBUG:
                print(f"[DEBUG] Error: {e}")
            return error_msg

    def chat_stream(self, user_message: str):
        """
        Send a message to JARVIS and get streaming response
        
        Args:
            user_message: User's message
            
        Yields:
            Chunks of JARVIS's response as they are generated
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Trim history if too long
        self._trim_history()
        
        full_response = ""
        
        try:
            # Call LLM API with streaming
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS,
                stream=True  # Enable streaming
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            # Add complete response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": full_response
            })
            
        except Exception as e:
            error_msg = f"抱歉，我遇到了一个问题: {str(e)}"
            if Config.DEBUG:
                print(f"[DEBUG] Error: {e}")
            yield error_msg

    def _handle_tool_calls(self, assistant_message) -> str:
        """Handle tool calling"""
        tool_calls = assistant_message.tool_calls
        
        # Add assistant's message with tool calls to history
        self.conversation_history.append(assistant_message)
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if Config.DEBUG:
                print(f"[DEBUG] Calling tool: {function_name} with {function_args}")
            
            # Find the tool
            result = "Tool not found"
            for tool_def in self.tools:
                # self.tools stores raw schemas, we need a way to map back to instances
                # For this simple prototype, we'll maintain a separate mapping or just search instances
                # Let's adjust register_tool to store instances instead
                pass

    def register_tool(self, tool_instance):
        """
        Register a new tool instance
        """
        # Store instance
        if not hasattr(self, 'tool_instances'):
            self.tool_instances = {}
            self.tools = [] # Clear existing if any
            
        self.tool_instances[tool_instance.name] = tool_instance
        self.tools.append(tool_instance.get_schema())

    def _handle_tool_calls(self, assistant_message) -> str:
        """Handle tool calling"""
        tool_calls = assistant_message.tool_calls
        
        # Add assistant's message with tool calls to history
        self.conversation_history.append(assistant_message)
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if Config.DEBUG:
                print(f"[DEBUG] Calling tool: {function_name} with {function_args}")
            
            # Execute tool
            if hasattr(self, 'tool_instances') and function_name in self.tool_instances:
                import asyncio
                # Execute async tool synchronously for this CLI prototype
                # In a real async app we would use await
                try:
                    # Quick hack for async execution in sync context for CLI
                    # In production we should make everything async
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                    result = loop.run_until_complete(
                        self.tool_instances[function_name].execute(**function_args)
                    )
                except Exception as e:
                    result = f"Error executing tool: {str(e)}"
            else:
                result = f"Tool {function_name} not implemented."
            
            # Give result back to AI
            self.conversation_history.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": str(result)
            })
            
        # Get follow-up response from AI
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS,
                tools=self.tools if self.tools else None
            )
            
            final_reply = response.choices[0].message.content
            
            # Add final reply to history
            self.conversation_history.append({
                "role": "assistant",
                "content": final_reply
            })
            
            return final_reply
            
        except Exception as e:
            return f"Error getting final response: {str(e)}"
    
    def clear_history(self):
        """Clear conversation history (keep system prompt)"""
        self.conversation_history = [self.conversation_history[0]]
    
    def get_stats(self) -> Dict:
        """Get conversation statistics"""
        return {
            "messages": len(self.conversation_history) - 1,  # Exclude system prompt
            "tools": len(self.tools)
        }

    def _trim_history(self):
        """Trim conversation history to configured limit"""
        if len(self.conversation_history) > Config.MAX_CONTEXT_MESSAGES + 1: # +1 for system prompt
            # Keep system prompt (index 0) and last MAX_CONTEXT_MESSAGES
            self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-Config.MAX_CONTEXT_MESSAGES:]
