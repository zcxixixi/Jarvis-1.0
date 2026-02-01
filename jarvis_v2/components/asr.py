"""
Automatic Speech Recognition (ASR) Module
Wrapper around Doubao ASR
"""

import asyncio
from typing import Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import ASRConfig

class ASREngine:
    """
    Automatic Speech Recognition.
    
    Features:
    - Streaming recognition
    - Multiple language support
    - Connection management
    
    Usage:
        asr = ASREngine()
        text = await asr.transcribe(audio_bytes)
    """
    
    def __init__(self, config: ASRConfig = None):
        self.config = config or ASRConfig()
        
        print(f"Initializing ASR engine (provider: {self.config.provider})...")
        
        # Initialize client based on provider
        if self.config.provider == "doubao":
            self._init_doubao()
        else:
            raise ValueError(f"Unknown ASR provider: {self.config.provider}")
    
    def _init_doubao(self):
        """Initialize Doubao STT client"""
        try:
            # Import Doubao client from existing codebase
            from jarvis_assistant.core.doubao_realtime_jarvis import DoubaoRealtimeJarvis
            
            # We'll use the existing STT implementation
            # For now, create a minimal client
            self.client = None
            print("✅ ASR engine ready (Doubao)")
            
        except Exception as e:
            print(f"⚠️ Failed to initialize Doubao ASR: {e}")
            self.client = None
    
    async def transcribe(
        self,
        audio: bytes,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio to text.
        
        Args:
            audio: Raw audio bytes (16-bit PCM, 16kHz)
            language: Language code (uses config default if None)
            
        Returns:
            str: Transcribed text
        """
        if not audio:
            return ""
        
        language = language or self.config.language
        
        # TODO: Implement actual transcription
        # For now, return placeholder
        print(f"📝 [STT] Transcribing {len(audio)} bytes (language: {language})")
        
        # This will be implemented using the existing Doubao connection
        # from DoubaoRealtimeJarvis
        
        return "[STT placeholder - to be integrated]"
    
    async def transcribe_stream(
        self,
        audio_stream,
        callback
    ):
        """
        Transcribe streaming audio.
        
        Args:
            audio_stream: AsyncGenerator of audio chunks
            callback: Function to call with partial results
        """
        async for chunk in audio_stream:
            partial_result = await self.transcribe(chunk)
            if callback:
                await callback(partial_result)
