# 🔧 Jarvis Modular Refactoring Plan
## Breaking Down 2682 Lines into Reusable Modules

**Problem:** `hybrid_jarvis.py` is doing everything:
- Audio I/O (PyAudio)
- Wake word detection
- VAD (Voice Activity Detection)  
- State management
- TTS pooling
- Agent logic
- Tool execution
- S2S routing
- Echo cancellation

**Goal:** Split into **small, testable, reusable modules** using **open-source libraries**

---

## 📊 Current Structure Analysis

```
hybrid_jarvis.py (2682 lines)
├── Class HybridJarvis (67 methods)
│   ├── Audio Management (~400 lines)
│   │   ├── setup_audio()
│   │   ├── _mic_reader_thread()
│   │   ├── _speaker_worker()
│   │   └── _play_audio_data()
│   │
│   ├── TTS Management (~600 lines)
│   │   ├── _speak_tool_result()
│   │   ├── _speak_stream()
│   │   ├── _speak_v3()
│   │   ├── _prepare_tts_capture()
│   │   └── _finalize_tts_capture()
│   │
│   ├── Tool Execution (~400 lines)
│   │   ├── _try_tool_shortcuts()
│   │   ├── _execute_tool_with_streaming()
│   │   └── Various tool handlers
│   │
│   ├── State Management (~300 lines)
│   │   ├── _transition_to_active()
│   │   ├── _transition_to_standby()
│   │   └── State tracking
│   │
│   ├── WebSocket Handlers (~500 lines)
│   │   ├── on_audio_stream()
│   │   ├── on_text_stream()
│   │   └── receive_loop()
│   │
│   └── Routing & Logic (~482 lines)
│       ├── on_text_received()
│       ├── handle_trigger()
│       └── QueryRouter integration
```

---

## 🎯 New Modular Architecture

### Option 1: Using Pipecat Framework (Recommended)

```
jarvis_v2/
├── main.py                      # Entry point (50 lines)
├── config.py                    # All configuration (100 lines)
│
├── components/                  # Reusable components
│   ├── __init__.py
│   ├── audio_io.py             # PyAudio wrapper (200 lines)
│   ├── vad.py                  # VAD using Silero (100 lines)
│   ├── wake_word.py            # OpenWakeWord wrapper (100 lines)
│   ├── stt.py                  # Doubao STT client (150 lines)
│   ├── tts.py                  # Doubao TTS pool (200 lines)
│   └── aec.py                  # Echo cancellation (150 lines)
│
├── pipeline/                    # Pipecat-style pipeline
│   ├── __init__.py
│   ├── base.py                 # Pipeline base classes (100 lines)
│   ├── voice_pipeline.py       # Main voice pipeline (250 lines)
│   └── processors/             # Pipeline processors
│       ├── noise_filter.py
│       ├── voice_detector.py
│       └── speech_recognizer.py
│
├── agent/                       # Agent logic
│   ├── __init__.py
│   ├── jarvis_agent.py         # Main agent (300 lines)
│   ├── tools/                  # Tool wrappers
│   │   ├── weather.py
│   │   ├── music.py
│   │   └── ...
│   └── memory.py               # Conversation memory (100 lines)
│
├── session/                     # Session management
│   ├── __init__.py
│   ├── session.py              # JarvisSession (300 lines)
│   └── state.py                # State machine (100 lines)
│
└── utils/                       # Utilities
    ├── __init__.py
    ├── audio_utils.py          # Existing utils
    └── text_utils.py           # Existing utils
```

### Key Benefits:
✅ Each file < 300 lines (easy to understand)
✅ AI can read and modify one module at a time
✅ Easy to test each component independently
✅ Can swap components (e.g., switch TTS provider)

---

## 📦 Open-Source Modules to Use

### 1. **Audio Pipeline: Use Pipecat's Pipeline Pattern**

**What to install:**
```bash
pip install pipecat-ai
```

**What we can reuse:**
- `pipecat.pipeline.Pipeline` - Base pipeline class
- `pipecat.frames.Frame` - Data frame format
- `pipecat.processors.BaseProcessor` - Processor interface

**Example:**
```python
from pipecat.pipeline import Pipeline
from pipecat.processors import BaseProcessor

class VoicePipeline(Pipeline):
    def __init__(self):
        super().__init__()
        
        # Add processors in order
        self.add_processor(NoiseFilter())
        self.add_processor(VoiceActivityDetector())
        self.add_processor(SpeechRecognizer())
        self.add_processor(IntentRouter())
        self.add_processor(AgentProcessor())
        self.add_processor(TextToSpeech())
```

### 2. **VAD: Use Silero VAD**

**What to install:**
```bash
pip install silero-vad
```

**What we can reuse:**
```python
from silero_vad import load_silero_vad, get_speech_timestamps

class VoiceActivityDetector:
    def __init__(self):
        self.model = load_silero_vad()
    
    def is_speech(self, audio_chunk):
        # Returns probability 0.0 - 1.0
        return self.model(audio_chunk, 16000)
```

### 3. **Session Management: Use LiveKit Agent Pattern**

**What to install:**
```bash
pip install livekit-agents
```

**What we can reuse:**
- Session lifecycle management
- Event-driven architecture
- Multi-agent coordination

**Example:**
```python
from livekit.agents import AgentSession

class JarvisSession(AgentSession):
    def __init__(self, config):
        self.config = config
        self.state = "STANDBY"
        self.components = self._init_components()
    
    async def start(self):
        """Start all components"""
        await asyncio.gather(
            self.components.wake_word.start(),
            self.components.vad.start(),
            self.components.stt.start(),
            self.components.agent.start(),
            self.components.tts.start(),
        )
```

### 4. **Agent: Use LangGraph for Complex Reasoning**

**What to install:**
```bash
pip install langgraph
```

**What we can reuse:**
- Graph-based agent orchestration
- Tool calling framework
- State management

**Example:**
```python
from langgraph.graph import StateGraph, END

# Define agent workflow
workflow = StateGraph()
workflow.add_node("classify_intent", classify_node)
workflow.add_node("call_tools", tools_node)
workflow.add_node("generate_response", response_node)
workflow.add_edge("classify_intent", "call_tools")
workflow.add_edge("call_tools", "generate_response")
workflow.add_edge("generate_response", END)
```

---

## 🚀 Step-by-Step Migration Guide

### Phase 1: Extract Audio Components (Week 1)

**Goal:** Isolate audio I/O from business logic

#### Step 1.1: Create `components/audio_io.py`

```python
"""
Audio I/O Module - Handles microphone and speaker
Replaces: hybrid_jarvis.py lines 707-904
"""

import pyaudio
import asyncio
from typing import Callable, Optional
from dataclasses import dataclass

@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 480  # 30ms at 16kHz
    format: int = pyaudio.paInt16

class AudioIO:
    """
    Manages audio input/output.
    
    Usage:
        audio = AudioIO()
        await audio.start()
        
        # Read from mic
        async for chunk in audio.read_stream():
            process(chunk)
        
        # Write to speaker
        await audio.write(audio_data)
    """
    
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig()
        self.pyaudio = pyaudio.PyAudio()
        
        self._mic_stream = None
        self._speaker_stream = None
        self._is_running = False
        
        # Queues
        self._mic_queue = asyncio.Queue(maxsize=100)
        self._speaker_queue = asyncio.Queue(maxsize=100)
    
    async def start(self):
        """Initialize audio streams"""
        self._is_running = True
        
        # Open microphone
        self._mic_stream = self.pyaudio.open(
            rate=self.config.sample_rate,
            channels=self.config.channels,
            format=self.config.format,
            input=True,
            frames_per_buffer=self.config.chunk_size,
            stream_callback=self._mic_callback
        )
        
        # Open speaker
        self._speaker_stream = self.pyaudio.open(
            rate=self.config.sample_rate,
            channels=2,  # Stereo
            format=self.config.format,
            output=True,
            frames_per_buffer=self.config.chunk_size,
        )
        
        # Start worker tasks
        asyncio.create_task(self._speaker_worker())
    
    async def read_stream(self):
        """Async generator for mic input"""
        while self._is_running:
            try:
                chunk = await asyncio.wait_for(
                    self._mic_queue.get(),
                    timeout=0.1
                )
                yield chunk
            except asyncio.TimeoutError:
                continue
    
    async def write(self, audio_data: bytes):
        """Write audio to speaker"""
        await self._speaker_queue.put(audio_data)
    
    def _mic_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback (runs in separate thread)"""
        try:
            self._mic_queue.put_nowait(in_data)
        except asyncio.QueueFull:
            pass  # Drop frame if queue full
        return (None, pyaudio.paContinue)
    
    async def _speaker_worker(self):
        """Async worker to play audio"""
        while self._is_running:
            try:
                data = await asyncio.wait_for(
                    self._speaker_queue.get(),
                    timeout=0.1
                )
                self._speaker_stream.write(data)
            except asyncio.TimeoutError:
                continue
    
    async def stop(self):
        """Clean shutdown"""
        self._is_running = False
        if self._mic_stream:
            self._mic_stream.stop_stream()
            self._mic_stream.close()
        if self._speaker_stream:
            self._speaker_stream.stop_stream()
            self._speaker_stream.close()
        self.pyaudio.terminate()
```

**Test it:**
```python
# test_audio_io.py
import asyncio
from components.audio_io import AudioIO

async def test():
    audio = AudioIO()
    await audio.start()
    
    print("Recording 3 seconds...")
    chunks = []
    async for chunk in audio.read_stream():
        chunks.append(chunk)
        if len(chunks) >= 100:  # ~3 seconds
            break
    
    print("Playing back...")
    for chunk in chunks:
        await audio.write(chunk)
    
    await asyncio.sleep(3)
    await audio.stop()

asyncio.run(test())
```

#### Step 1.2: Create `components/vad.py`

```python
"""
Voice Activity Detection using Silero VAD
Replaces: Parts of hybrid_jarvis.py VAD logic
"""

import torch
import numpy as np
from typing import Optional

class VoiceActivityDetector:
    """
    Detects speech vs silence in audio stream.
    
    Usage:
        vad = VoiceActivityDetector()
        
        for chunk in audio_stream:
            if vad.is_speech(chunk):
                print("User is speaking")
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 500
    ):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_ms = min_speech_duration_ms
        self.min_silence_ms = min_silence_duration_ms
        
        # Load Silero VAD model
        self.model, _ = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False
        )
        
        # State
        self._speech_start = None
        self._silence_start = None
        self._is_speaking = False
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Check if audio chunk contains speech.
        Returns True if speech probability > threshold.
        """
        # Convert bytes to tensor
        audio_int16 = np.frombuffer(audio_chunk, np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float32)
        
        # Get speech probability
        with torch.no_grad():
            speech_prob = self.model(audio_tensor, self.sample_rate).item()
        
        return speech_prob > self.threshold
    
    def get_speech_timestamps(
        self,
        audio_chunks: list
    ) -> list:
        """
        Get precise timestamps of speech segments.
        Returns [(start_ms, end_ms), ...]
        """
        # Concatenate chunks
        audio = b''.join(audio_chunks)
        audio_int16 = np.frombuffer(audio, np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        # Use Silero's built-in timestamp detection
        from silero_vad import get_speech_timestamps
        
        timestamps = get_speech_timestamps(
            torch.from_numpy(audio_float32),
            self.model,
            sampling_rate=self.sample_rate,
            threshold=self.threshold,
            min_speech_duration_ms=self.min_speech_ms,
            min_silence_duration_ms=self.min_silence_ms
        )
        
        return [(ts['start'], ts['end']) for ts in timestamps]
```

#### Step 1.3: Create `components/wake_word.py`

```python
"""
Wake Word Detection using OpenWakeWord
Replaces: Parts of hybrid_jarvis.py wake word logic
"""

import openwakeword
from openwakeword.model import Model as WakeWordModel
import numpy as np

class WakeWordDetector:
    """
    Detects wake words like "Hey Jarvis".
    
    Usage:
        detector = WakeWordDetector(["hey_jarvis"])
        
        for audio_chunk in stream:
            if detector.detect(audio_chunk):
                print("Wake word detected!")
    """
    
    def __init__(
        self,
        models: list = None,
        threshold: float = 0.5
    ):
        self.threshold = threshold
        
        # Load models
        models = models or ["hey_jarvis_v0.1"]
        self.wake_word_model = WakeWordModel(
            wakeword_models=models,
            inference_framework='onnx'
        )
        
        self.last_detection = 0
        self.debounce_seconds = 2.0
    
    def detect(self, audio_chunk: bytes) -> Optional[str]:
        """
        Check if wake word is present.
        Returns wake word name if detected, None otherwise.
        """
        import time
        
        # Debounce
        now = time.time()
        if now - self.last_detection < self.debounce_seconds:
            return None
        
        # Convert to numpy array
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        # Run detection
        predictions = self.wake_word_model.predict(audio_float32)
        
        # Check all models
        for model_name, score in predictions.items():
            if score > self.threshold:
                self.last_detection = now
                return model_name
        
        return None
```

### Phase 2: Extract TTS Component (Week 1)

#### Step 2.1: Create `components/tts.py`

```python
"""
Text-to-Speech with connection pooling
Replaces: hybrid_jarvis.py TTS methods + tts_v3.py
"""

import asyncio
from typing import AsyncGenerator
from jarvis_assistant.services.doubao.tts_v3 import DoubaoTTSV1

class TTSPool:
    """
    Singleton TTS with connection pooling.
    Reuses WebSocket connections for lower latency.
    
    Usage:
        tts = TTSPool()
        
        async for audio_chunk in tts.synthesize("Hello world"):
            play(audio_chunk)
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.client = DoubaoTTSV1()
        self._lock = asyncio.Lock()
        self._initialized = True
    
    async def synthesize(
        self,
        text: str,
        voice: str = "zh_female_shuangkuaisisi_moon_bigtts"
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text to speech.
        Yields audio chunks as they're generated.
        """
        async with self._lock:
            # Ensure connection
            await self.client._ensure_connected()
            
            # Synthesize
            async for chunk in self.client.synthesize(text, voice=voice):
                yield chunk
    
    async def close(self):
        """Close connection"""
        if self.client:
            await self.client.close()
```

### Phase 3: Create Session Manager (Week 2)

#### Step 3.1: Create `session/session.py`

```python
"""
JarvisSession - Orchestrates all components
Replaces: Most of hybrid_jarvis.py
"""

import asyncio
from dataclasses import dataclass
from enum import Enum

from components.audio_io import AudioIO, AudioConfig
from components.vad import VoiceActivityDetector
from components.wake_word import WakeWordDetector
from components.stt import SpeechRecognizer  # To be created
from components.tts import TTSPool
from agent.jarvis_agent import JarvisAgent  # To be created

class SessionState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

@dataclass
class SessionConfig:
    audio: AudioConfig = None
    vad_threshold: float = 0.5
    wake_word_models: list = None

class JarvisSession:
    """
    Main session orchestrator.
    Manages the lifecycle of a voice conversation.
    
    This is the replacement for 2682-line HybridJarvis class.
    Now it's just a coordinator - each component is separate.
    """
    
    def __init__(self, config: SessionConfig = None):
        self.config = config or SessionConfig()
        self.state = SessionState.IDLE
        
        # Initialize components
        self.audio = AudioIO(self.config.audio)
        self.vad = VoiceActivityDetector(threshold=self.config.vad_threshold)
        self.wake_word = WakeWordDetector(self.config.wake_word_models)
        self.stt = SpeechRecognizer()
        self.tts = TTSPool()
        self.agent = JarvisAgent()
        
        # State
        self._is_running = False
        self._speech_buffer = []
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start the session"""
        self._is_running = True
        
        # Start audio
        await self.audio.start()
        
        print("🎙️ Jarvis is ready!")
        
        # Run main loops
        await asyncio.gather(
            self._wake_word_loop(),
            self._voice_loop(),
            self._agent_loop(),
        )
    
    async def _wake_word_loop(self):
        """Continuously listen for wake word"""
        async for chunk in self.audio.read_stream():
            if self.state != SessionState.IDLE:
                continue
            
            wake_word = self.wake_word.detect(chunk)
            if wake_word:
                print(f"🎤 Wake word detected: {wake_word}")
                await self._on_wake_word()
    
    async def _voice_loop(self):
        """Handle voice activity detection"""
        async for chunk in self.audio.read_stream():
            if self.state != SessionState.LISTENING:
                continue
            
            is_speech = self.vad.is_speech(chunk)
            
            if is_speech:
                self._speech_buffer.append(chunk)
            elif self._speech_buffer:
                # End of speech
                await self._on_speech_end()
    
    async def _agent_loop(self):
        """Process user requests through agent"""
        # This will be implemented with message queue
        pass
    
    async def _on_wake_word(self):
        """Handle wake word detection"""
        self.state = SessionState.LISTENING
        # Play acknowledgment sound
        # Clear speech buffer
        self._speech_buffer = []
    
    async def _on_speech_end(self):
        """Handle end of user speech"""
        self.state = SessionState.PROCESSING
        
        # Transcribe
        audio = b''.join(self._speech_buffer)
        text = await self.stt.transcribe(audio)
        
        print(f"👤 User: {text}")
        
        # Get agent response
        async for response_chunk in self.agent.respond(text):
            # Synthesize
            async for audio_chunk in self.tts.synthesize(response_chunk):
                await self.audio.write(audio_chunk)
        
        # Back to idle
        self.state = SessionState.IDLE
        self._speech_buffer = []
    
    async def stop(self):
        """Stop the session"""
        self._is_running = False
        await self.audio.stop()
        await self.tts.close()
```

### Phase 4: Create Clean Entry Point (Week 2)

#### Step 4.1: Create `main.py`

```python
"""
Jarvis Voice Assistant - Clean Entry Point
Total lines: ~50 (vs 2682 before!)
"""

import asyncio
from session.session import JarvisSession, SessionConfig
from components.audio_io import AudioConfig

async def main():
    # Configuration
    config = SessionConfig(
        audio=AudioConfig(
            sample_rate=16000,
            chunk_size=480
        ),
        vad_threshold=0.5,
        wake_word_models=["hey_jarvis_v0.1"]
    )
    
    # Create session
    session = JarvisSession(config)
    
    # Play boot sound
    from jarvis_assistant.utils.audio_utils import play_boot_sound
    play_boot_sound()
    
    # Run
    try:
        await session.start()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    finally:
        await session.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Now the codebase is:**
- ✅ Modular (each file < 300 lines)
- ✅ Testable (can test each component)
- ✅ Debuggable (easy to find bugs)
- ✅ Maintainable (AI can modify one file at a time)

---

## 📋 Migration Checklist

### Week 1: Foundation
- [ ] Create new `jarvis_v2/` directory
- [ ] Install dependencies (pipecat, silero-vad, etc.)
- [ ] Extract `components/audio_io.py`
- [ ] Extract `components/vad.py`
- [ ] Extract `components/wake_word.py`
- [ ] Extract `components/tts.py`
- [ ] Test each component independently

### Week 2: Integration
- [ ] Create `session/session.py`
- [ ] Create `session/state.py` (state machine)
- [ ] Create `main.py`
- [ ] Wire components together
- [ ] Test basic voice loop

### Week 3: Agent Migration
- [ ] Extract existing Agent logic
- [ ] Create `agent/jarvis_agent.py`
- [ ] Migrate tool system
- [ ] Test agent responses

### Week 4: Polish & Testing
- [ ] Migrate remaining features
- [ ] Add comprehensive tests
- [ ] Performance testing
- [ ] Documentation
- [ ] Switch from `hybrid_jarvis.py` to new system

---

## 🎯 Success Metrics

**Before (Current):**
- ❌ One file: 2682 lines
- ❌ 67 methods in one class
- ❌ Hard to debug
- ❌ Hard to test
- ❌ AI struggles to modify

**After (Target):**
- ✅ Main file: ~50 lines
- ✅ Largest module: ~300 lines
- ✅ 100% test coverage
- ✅ Each component independently testable
- ✅ AI can modify one module at a time

---

## 🚦 Next Steps

**Immediate (This Week):**
1. Create `jarvis_v2/` directory structure
2. Extract `AudioIO` component
3. Write tests for `AudioIO`
4. Verify it works standalone

**Want me to start implementing?** I can:
1. Create the directory structure
2. Implement the first component (`AudioIO`)
3. Write tests
4. Show you it works

Just say "start implement" and I'll begin! 🚀
