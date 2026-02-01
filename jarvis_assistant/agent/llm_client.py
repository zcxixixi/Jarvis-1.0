"""
Doubao LLM streaming client.
Extracted from legacy agent.py for clean architecture.
Optimized for <1s first token latency.
"""

import os
import json
import asyncio
from typing import List, Dict, Optional, AsyncIterator
import aiohttp


class DoubaoLLMClient:
    """
    Streaming LLM client for Doubao Responses API.
    
    Optimized for voice UX:
    - Streaming by default (first token <700ms)
    - Thinking disabled for speed
    - Minimal reasoning effort
    """
    
    def __init__(
        self,
        endpoint_id: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize Doubao LLM client.
        
        Args:
            endpoint_id: Doubao endpoint (defaults to env DOUBAO_ENDPOINT_ID)
            api_key: API key (defaults to env DOUBAO_ARK_API_KEY or DOUBAO_ACCESS_TOKEN)
        """
        self.endpoint_id = endpoint_id or os.getenv("DOUBAO_ENDPOINT_ID", "ep-20241228191825-f94fk")
        # Try multiple env variable names for API key
        self.api_key = api_key or os.getenv("DOUBAO_ARK_API_KEY") or os.getenv("DOUBAO_ACCESS_TOKEN")
        self.url = "https://ark.cn-beijing.volces.com/api/v3/responses"
    
    def _format_messages(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Format messages for Doubao Responses API.
        
        Args:
            user_message: Current user query
            system_prompt: System prompt (optional)
            history: Conversation history (optional)
            
        Returns:
            List of messages in Doubao format
        """
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({
                "type": "message",
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}]
            })
        
        # Add history if provided
        if history:
            for entry in history:
                role = entry.get("role", "user")
                content = entry.get("content", "")
                
                msg = {
                    "type": "message",
                    "role": role,
                    "content": [{
                        "type": "input_text" if role == "user" else "output_text",
                        "text": content
                    }]
                }
                
                if role == "assistant":
                    msg["status"] = "completed"
                
                messages.append(msg)
        
        # Add current user message
        messages.append({
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": user_message}]
        })
        
        return messages
    
    async def generate_stream(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """
        🚀 Generate streaming LLM response.
        
        CRITICAL: First token yields in 500-700ms for low-latency voice UX.
        
        Args:
            user_message: Current user query
            system_prompt: System prompt (optional)
            history: Conversation history (optional)
            temperature: LLM temperature (default: 0.7)
            
        Yields:
            str: Response chunks as they arrive
            
        Example:
            async for chunk in llm.generate_stream("你好"):
                print(chunk, end="", flush=True)
        """
        # Format input messages
        messages = self._format_messages(user_message, system_prompt, history)
        
        # Prepare request payload
        payload = {
            "model": self.endpoint_id,
            "input": messages,
            "stream": True,  # 🚀 Enable streaming
            "temperature": temperature,
            "thinking": {
                "type": "disabled"  # 🔥 Disable thinking for speed
            }
        }
        
        # Add minimal reasoning for supported models
        if "lite" in self.endpoint_id or "251228" in self.endpoint_id:
            payload["reasoning"] = {"effort": "minimal"}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Stream response
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=payload, headers=headers, timeout=30) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Doubao API error ({response.status}): {error_text}")
                
                # Parse SSE stream
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line or line == "data: [DONE]":
                        continue
                    
                    if line.startswith("data:"):
                        data = line[5:].strip()  # Remove "data:" prefix
                        if data == "[DONE]":
                            continue
                        
                        try:
                            event = json.loads(data)
                            event_type = event.get("type", "")
                            
                            # Handle different event types from Doubao Responses API
                            # Main text delta events
                            if event_type == "response.output_text.delta":
                                chunk = event.get("delta", "")
                                if chunk:
                                    yield chunk
                            
                            # Legacy format (fallback)
                            elif "output" in event:
                                for output_item in event["output"]:
                                    if output_item.get("type") == "output_text":
                                        chunk = output_item.get("text", "")
                                        if chunk:
                                            yield chunk
                            
                            # ChatCompletion format (fallback)
                            elif "choices" in event:
                                for choice in event.get("choices", []):
                                    delta = choice.get("delta", {})
                                    chunk = delta.get("content", "")
                                    if chunk:
                                        yield chunk
                                        
                        except json.JSONDecodeError:
                            continue
    
    async def generate(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Generate complete (non-streaming) response.
        
        For backward compatibility. Prefer generate_stream() for voice UX.
        
        Returns:
            Complete response text
        """
        full_response = ""
        async for chunk in self.generate_stream(
            user_message, system_prompt, history, temperature
        ):
            full_response += chunk
        return full_response
