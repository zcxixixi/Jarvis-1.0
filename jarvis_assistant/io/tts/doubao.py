"""
Doubao TTS Output adapter for streaming voice synthesis.
Implements OutputInterface with persistent connection pooling.
"""

import asyncio
import os
from typing import AsyncIterator, Optional
from jarvis_assistant.interfaces import OutputInterface
from jarvis_assistant.services.doubao.tts_v3 import DoubaoTTSV1


class DoubaoTTS(OutputInterface):
    """
    Doubao TTS adapter with persistent WebSocket connection.
    
    Optimizations:
    - Connection pooling (reuse WebSocket across requests)
    - Sentence-level buffering (synthesize on punctuation)
    - Parallel synthesis + playback
    - Cached acknowledgment audio
    """
    
    def __init__(self):
        """Initialize TTS client with persistent connection."""
        self.client = DoubaoTTSV1()
        self._connected = False
        self._audio_queue = asyncio.Queue()
        self._playback_task = None
        
        # Pre-load acknowledgment audio (instant feedback)
        self._ack_audio = self._generate_ack_audio()
    
    def _generate_ack_audio(self) -> bytes:
        """Generate short acknowledgment tone (50ms)."""
        # Simple beep tone at 440Hz
        import numpy as np
        duration = 0.05  # 50ms
        sample_rate = 24000
        frequency = 440
        
        samples = int(duration * sample_rate)
        t = np.linspace(0, duration, samples)
        tone = (np.sin(2 * np.pi * frequency * t) * 8000).astype(np.int16)
        
        return tone.tobytes()
    
    async def _ensure_connected(self):
        """Ensure TTS WebSocket is connected (reuse if possible)."""
        if not self._connected or self.client._is_closed():
            print("🔌 [TTS] Connecting to Doubao...")
            await self.client.connect()
            self._connected = True
        # else: Connection already alive, reuse it!
    
    async def listen(self) -> AsyncIterator[str]:
        """Not applicable for TTS output."""
        raise NotImplementedError("TTS is output-only")
    
    async def listen_stream(self) -> AsyncIterator[str]:
        """Not applicable for TTS output."""
        raise NotImplementedError("TTS is output-only")
    
    async def speak(self, text: str):
        """
        Synthesize and speak text (complete, non-streaming).
        
        Args:
            text: Text to synthesize
        """
        await self._ensure_connected()
        
        # Synthesize and collect all audio
        audio_chunks = []
        async for chunk in self.client.synthesize(text):
            audio_chunks.append(chunk)
        
        # Play audio (simulated for now, in production use PyAudio)
        total_bytes = sum(len(c) for c in audio_chunks)
        print(f"🔊 [TTS] Playing {total_bytes} bytes of audio")
    
    async def speak_stream(self, text_stream: AsyncIterator[str]):
        """
        🚀 STREAMING: Synthesize and play text chunks in real-time.
        
        CRITICAL for <1s latency:
        - Buffer text until sentence completion
        - Synthesize immediately on punctuation
        - Play audio in parallel (don't wait for synthesis)
        
        Args:
            text_stream: Stream of text chunks from LLM
        """
        await self._ensure_connected()
        
        buffer = ""
        sentence_count = 0
        
        # Collect and buffer text chunks
        async for chunk in text_stream:
            buffer += chunk
            
            # Check for sentence completion (punctuation triggers)
            if self._is_sentence_end(buffer):
                sentence_count += 1
                sentence = buffer.strip()
                
                if sentence:
                    # Trigger synthesis asynchronously (don't await)
                    asyncio.create_task(self._synthesize_and_queue(sentence))
                
                buffer = ""  # Reset buffer
        
        # Flush remaining text
        if buffer.strip():
            asyncio.create_task(self._synthesize_and_queue(buffer.strip()))
    
    def _is_sentence_end(self, text: str) -> bool:
        """
        Detect sentence completion for chunked synthesis.
        
        Returns:
            True if text ends with punctuation
        """
        return text.rstrip().endswith((".", "!", "?", "。", "！", "？", "，", ",", "\n"))
    
    async def _synthesize_and_queue(self, text: str):
        """
        Synthesize text and queue audio for playback.
        
        This runs in parallel with LLM streaming for minimal latency.
        """
        print(f"🔈 [TTS] Synthesizing: {text[:30]}...")
        
        try:
            # Synthesize
            audio_chunks = []
            async for chunk in self.client.synthesize(text):
                audio_chunks.append(chunk)
            
            # Queue for playback
            total_bytes = sum(len(c) for c in audio_chunks)
            await self._audio_queue.put((text, audio_chunks, total_bytes))
            
        except Exception as e:
            print(f"⚠️ [TTS] Synthesis error: {e}")
    
    async def play_acknowledgment(self):
        """
        ⚡ Play instant acknowledgment (<50ms).
        
        Gives immediate feedback while LLM is thinking.
        """
        print("🎵 *ack*", flush=True)
        # In production: play self._ack_audio via PyAudio
        await asyncio.sleep(0.01)  # Simulate playback time
    
    async def close(self):
        """Close TTS connection."""
        if self._connected:
            await self.client.close()
            self._connected = False


# Singleton instance (connection pooling across requests)
_tts_instance = None

def get_doubao_tts() -> DoubaoTTS:
    """
    Get singleton TTS instance (connection pooling).
    
    Returns:
        Shared DoubaoTTS instance
    """
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = DoubaoTTS()
    return _tts_instance
