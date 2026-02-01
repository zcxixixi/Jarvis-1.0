"""
Abstract input interface - defines contract for input sources.
Implementations: ASR, console, API, websocket, etc.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class InputInterface(ABC):
    """
    Abstract input source for Jarvis.
    
    Any input implementation (ASR, console, API) must implement this interface.
    This allows the agent to work with ANY input source without modification.
    
    Examples:
        - DoubaoASR: Real-time speech-to-text
        - ConsoleInput: Text input from terminal (testing)
        - WebSocketInput: Input from web client
        - APIInput: Input from REST API
    """
    
    @abstractmethod
    async def listen(self) -> str:
        """
        Listen for user input and return complete text.
        
        For ASR: Wait for speech, transcribe, return when user stops talking.
        For console: Wait for Enter key, return typed text.
        For API: Wait for request, return text payload.
        
        Returns:
            str: Complete user input text
            
        Raises:
            InputError: If input fails (mic error, network timeout, etc.)
        """
        pass
    
    async def listen_stream(self) -> AsyncIterator[str]:
        """
        Stream user input as it arrives (optional, for low-latency).
        
        For ASR: Yield partial transcriptions as speech is processed.
        For console: Yield character by character (not typical).
        
        Yields:
            str: Partial input chunks
            
        Note:
            Default implementation calls listen() once.
            Override for true streaming support.
        """
        result = await self.listen()
        yield result
    
    async def wait_for_wake_word(self) -> bool:
        """
        Wait for activation phrase (optional, for voice assistants).
        
        For ASR: Listen for "Jarvis" or custom wake word.
        For console/API: Always return True (no wake word needed).
        
        Returns:
            bool: True if wake word detected, False if cancelled/timeout
            
        Note:
            Default implementation returns True (no wake word).
            Override for voice-activated systems.
        """
        return True
    
    async def close(self):
        """
        Cleanup resources (close connections, release mic, etc.).
        
        Note:
            Optional, default implementation does nothing.
            Override if your input needs cleanup.
        """
        pass
