"""
Text-to-Speech Module with Connection Pooling
Replaces TTS logic from hybrid_jarvis.py (~600 lines)
"""

import asyncio
from typing import AsyncGenerator, Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from jarvis_assistant.services.doubao.tts_v3 import DoubaoTTSV1
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import TTSConfig

class TTSEngine:
    """
    Text-to-Speech with connection pooling for lower latency.
    
    Features:
    - Connection reuse (590ms vs 670ms first call)
    - Streaming output
    - Singleton pattern
    - Multiple voice support
    
    Usage:
        tts = TTSEngine()
        
        async for audio_chunk in tts.synthesize("Hello world"):
            play(audio_chunk)
    """
    
    _instance: Optional['TTSEngine'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls, config: TTSConfig = None):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: TTSConfig = None):
        if self._initialized:
            return
        
        self.config = config or TTSConfig()
        
        # Initialize Doubao TTS client
        print("Initializing TTS engine...")
        try:
            self.client = DoubaoTTSV1()
            print(f"✅ TTS engine ready (voice: {self.config.voice})")
        except Exception as e:
            print(f"❌ Failed to initialize TTS: {e}")
            self.client = None
        
        self._synthesis_lock = asyncio.Lock()
        self._initialized = True
        self._synthesis_count = 0
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        stream: bool = True
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text to speech.
        
        Args:
            text: Text to synthesize
            voice: Voice ID (uses config default if None)
            stream: Whether to stream output
            
        Yields:
            bytes: Audio chunks (16-bit PCM)
        """
        if not self.client:
            print("❌ TTS client not initialized")
            return
        
        if not text or not text.strip():
            return
        
        voice = voice or self.config.voice
        
        async with self._synthesis_lock:
            self._synthesis_count += 1
            count = self._synthesis_count
            
            if count == 1:
                print(f"🔌 [TTS] First synthesis (will establish connection)")
            else:
                print(f"🔌 [TTS] Synthesis #{count} (reusing connection)")
            
            try:
                # Use existing TTS client with connection pooling
                async for chunk in self.client.synthesize(text, voice=voice):
                    yield chunk
                    
            except Exception as e:
                print(f"❌ TTS synthesis error: {e}")
    
    async def synthesize_quick(self, text: str) -> bytes:
        """
        Synthesize short text (non-streaming).
        Useful for quick acknowledgments.
        
        Args:
            text: Short text to synthesize
            
        Returns:
            bytes: Complete audio data
        """
        chunks = []
        async for chunk in self.synthesize(text):
            chunks.append(chunk)
        
        return b''.join(chunks)
    
    async def close(self):
        """Close TTS connection"""
        if self.client:
            try:
                await self.client.close()
                print("✅ TTS connection closed")
            except:
                pass
