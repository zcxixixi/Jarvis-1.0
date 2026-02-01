"""
Session Manager - Orchestrates all components
This is the HEART of Jarvis V2
Replaces the 2682-line HybridJarvis class!
"""

import asyncio
from enum import Enum
from typing import Optional
import time

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from components.audio_io import AudioIO
from components.vad import VoiceActivityDetector
from components.wake_word import WakeWordDetector
from components.asr import ASREngine
from components.tts import TTSEngine
from agent.jarvis_agent import JarvisAgent
from config import JarvisConfig

class SessionState(Enum):
    """Session states"""
    IDLE = "idle"              # Waiting for wake word
    LISTENING = "listening"    # Recording user speech
    PROCESSING = "processing"  # Thinking / calling tools
    SPEAKING = "speaking"      # Playing response

class JarvisSession:
    """
    Main session orchestrator.
    
    This replaces the 2682-line HybridJarvis class.
    Now it's just a coordinator - each component is separate!
    
    Flow:
    1. IDLE → wake word → LISTENING
    2. LISTENING → VAD detects silence → PROCESSING
    3. PROCESSING → agent responds → SPEAKING
    4. SPEAKING → done → IDLE
    
    Usage:
        config = JarvisConfig()
        session = JarvisSession(config)
        await session.start()
    """
    
    def __init__(self, config: JarvisConfig = None):
        self.config = config or JarvisConfig()
        
        print("\n" + "="*60)
        print("🚀 Initializing Jarvis V2 Session")
        print("="*60)
        
        # Initialize all components
        self.audio = AudioIO(self.config.audio)
        self.vad = VoiceActivityDetector(self.config.vad)
        self.wake_word = WakeWordDetector(self.config.wake_word)
        self.asr = ASREngine(self.config.asr)
        self.tts = TTSEngine(self.config.tts)
        self.agent = JarvisAgent(self.config.agent)
        
        # Session state
        self.state = SessionState.IDLE
        self._is_running = False
        
        # Speech buffer
        self._speech_buffer = []
        self._speech_start_time = 0.0
        
        # Locks
        self._state_lock = asyncio.Lock()
        
        print("✅ All components initialized")
        print("="*60 + "\n")
    
    async def start(self):
        """Start the session"""
        if self._is_running:
            print("⚠️ Session already running")
            return
        
        self._is_running = True
        
        # Start audio I/O
        await self.audio.start()
        
        # Play boot sound if enabled
        if self.config.enable_boot_sound:
            self._play_boot_sound()
        
        print("\n🎙️ Jarvis is ready! Say 'Hey Jarvis' to activate.\n")
        
        # Run main loop
        try:
            await self._main_loop()
        except KeyboardInterrupt:
            print("\n⚠️ Session interrupted by user")
        finally:
            await self.stop()
    
    async def _main_loop(self):
        """Main event loop"""
        
        async for audio_chunk in self.audio.read_stream():
            if not self._is_running:
                break
            
            # State machine
            if self.state == SessionState.IDLE:
                await self._handle_idle(audio_chunk)
            
            elif self.state == SessionState.LISTENING:
                await self._handle_listening(audio_chunk)
            
            # PROCESSING and SPEAKING states don't process audio
    
    async def _handle_idle(self, audio_chunk: bytes):
        """Handle IDLE state - listen for wake word"""
        
        wake_word = self.wake_word.detect(audio_chunk)
        
        if wake_word:
            print(f"\n🎤 Wake word detected: {wake_word}")
            await self._transition_to_listening()
    
    async def _handle_listening(self, audio_chunk: bytes):
        """Handle LISTENING state - record user speech"""
        
        # Check for speech
        is_speech, event = self.vad.process_stream(audio_chunk)
        
        if event == "speech_start":
            print("🗣️ User started speaking...")
            self._speech_start_time = time.time()
            self._speech_buffer = [audio_chunk]
        
        elif event == "speaking":
            self._speech_buffer.append(audio_chunk)
        
        elif event == "speech_end":
            duration = time.time() - self._speech_start_time
            print(f"✅ Speech ended ({duration:.1f}s)")
            
            # Process the speech
            await self._process_speech()
    
    async def _process_speech(self):
        """Process recorded speech"""
        
        if not self._speech_buffer:
            print("⚠️ No speech recorded")
            await self._transition_to_idle()
            return
        
        # Transition to PROCESSING
        await self._transition_to_processing()
        
        # Concatenate audio
        audio = b''.join(self._speech_buffer)
        self._speech_buffer = []
        
        # Transcribe
        print("📝 Transcribing...")
        text = await self.asr.transcribe(audio)
        
        if not text or text.startswith("[STT placeholder"):
            print("⚠️ No transcription, returning to idle")
            await self._transition_to_idle()
            return
        
        print(f"👤 User: {text}")
        
        # Get agent response
        print("🧠 Thinking...")
        
        await self._transition_to_speaking()
        
        async for response_chunk in self.agent.respond(text):
            print(f"🤖 Jarvis: {response_chunk}")
            
            # Synthesize and play
            async for audio_chunk in self.tts.synthesize(response_chunk):
                await self.audio.write(audio_chunk)
        
        # Wait for audio to finish playing
        await asyncio.sleep(0.5)
        
        # Back to idle
        await self._transition_to_idle()
    
    async def _transition_to_listening(self):
        """Transition to LISTENING state"""
        async with self._state_lock:
            self.state = SessionState.LISTENING
            self.vad.reset()
            self._speech_buffer = []
            print("[STATE] 🟢 IDLE → LISTENING")
    
    async def _transition_to_processing(self):
        """Transition to PROCESSING state"""
        async with self._state_lock:
            self.state = SessionState.PROCESSING
            print("[STATE] 🟡 LISTENING → PROCESSING")
    
    async def _transition_to_speaking(self):
        """Transition to SPEAKING state"""
        async with self._state_lock:
            self.state = SessionState.SPEAKING
            print("[STATE] 🔵 PROCESSING → SPEAKING")
    
    async def _transition_to_idle(self):
        """Transition to IDLE state"""
        async with self._state_lock:
            self.state = SessionState.IDLE
            self.vad.reset()
            self.wake_word.reset()
            print("[STATE] 🔴 → IDLE")
    
    def _play_boot_sound(self):
        """Play boot sound"""
        try:
            from jarvis_assistant.utils.audio_utils import play_boot_sound
            play_boot_sound()
        except Exception as e:
            print(f"⚠️ Could not play boot sound: {e}")
    
    async def stop(self):
        """Stop the session"""
        print("\n🛑 Stopping Jarvis session...")
        
        self._is_running = False
        
        # Stop audio
        await self.audio.stop()
        
        # Close TTS
        await self.tts.close()
        
        print("✅ Session stopped")
