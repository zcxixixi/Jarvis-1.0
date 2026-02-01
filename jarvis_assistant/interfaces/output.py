"""
Abstract output interface - defines contract for output sinks.
Implementations: TTS, console, websocket, API response, etc.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class OutputInterface(ABC):
    """
    Abstract output sink for Jarvis.
    
    Any output implementation (TTS, console, API) must implement this interface.
    This allows the agent to work with ANY output sink without modification.
    
    CRITICAL for Voice UX: Must support streaming for <1s first token latency!
    
    Examples:
        - DoubaoTTS: Text-to-speech synthesis
        - ConsoleOutput: Print to terminal (testing)
        - WebSocketOutput: Send to web client
        - APIOutput: Return as REST API response
    """
    
    @abstractmethod
    async def speak(self, text: str):
        """
        Output complete text response.
        
        For TTS: Synthesize entire text to audio, play it.
        For console: Print complete text.
        For API: Send complete response.
        
        Args:
            text: Complete agent response
            
        Raises:
            OutputError: If output fails (TTS error, network timeout, etc.)
        """
        pass
    
    @abstractmethod
    async def speak_stream(self, text_stream: AsyncIterator[str]):
        """
        🚀 CRITICAL: Stream output as it's generated (REQUIRED for <1s latency).
        
        For TTS: Synthesize and play audio chunks as text arrives.
        For console: Print text chunks as they arrive.
        
        This is NOT optional for voice agents - streaming is essential for UX!
        
        Args:
            text_stream: Async generator yielding text chunks
            
        Note:
            Default implementation collects all chunks then calls speak().
            ⚠️  Override for true streaming support (lower latency).
        """
        full_text = ""
        async for chunk in text_stream:
            full_text += chunk
        await self.speak(full_text)
    
    async def play_acknowledgment(self):
        """
        🎯 INSTANT feedback for voice UX (<50ms target).
        
        Play immediate acknowledgment sound/phrase while processing query.
        User gets instant feedback = perceived latency near zero!
        
        Examples:
            - Play beep/tone (50ms audio file)
            - Speak "Mm-hmm" / "让我想想" (pre-cached audio)
            - Visual: Show "listening" animation
        
        Note:
            Default implementation does nothing.
            Override for voice agents to improve perceived responsiveness!
        """
        pass
    
    async def show_thinking(self, message: str):
        """
        Show intermediate status/thinking (optional, for UX).
        
        For TTS: Play "thinking" sound or speak status.
        For console: Print status message.
        For API: Send status event.
        
        Args:
            message: Status message (e.g., "Searching the web...", "Calling tool...")
            
        Note:
            Default implementation does nothing.
            Override for better UX during long operations.
        """
        pass
    
    async def close(self):
        """
        Cleanup resources (close audio stream, network connections, etc.).
        
        Note:
            Optional, default implementation does nothing.
            Override if your output needs cleanup.
        """
        pass
