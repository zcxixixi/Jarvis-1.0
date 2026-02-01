# 🤖 Building a Super Intelligent Jarvis Agent
## A Complete Tutorial Based on Industry Best Practices

*Reference Projects: [Pipecat](https://github.com/pipecat-ai/pipecat) & [LiveKit Agents](https://github.com/livekit/agents)*

---

## 📚 Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Core Concepts](#2-core-concepts)
3. [Building Blocks](#3-building-blocks)
4. [Implementation Guide](#4-implementation-guide)
5. [Improving Your Current Jarvis](#5-improving-your-current-jarvis)
6. [Advanced Patterns](#6-advanced-patterns)
7. [UX Best Practices](#7-ux-best-practices)

---

## 1. Architecture Overview

### 🏗️ The Modern Voice AI Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION                          │
│                   🎤 Voice / 💬 Text / 📱 App                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      TRANSPORT LAYER                             │
│        WebSocket / WebRTC / Local Audio (PyAudio)                │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       PIPELINE (Pipecat Style)                   │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐      │
│  │   VAD    │ → │   STT    │ → │   LLM    │ → │   TTS    │      │
│  │(Silero)  │   │(Doubao)  │   │(Agent)   │   │(Doubao)  │      │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘      │
│                                      │                           │
│                               ┌──────┴──────┐                    │
│                               │    TOOLS    │                    │
│                               │ (Weather,   │                    │
│                               │  Music, etc)│                    │
│                               └─────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         AUDIO OUTPUT                             │
│                   🔊 Speaker / Bluetooth                         │
└─────────────────────────────────────────────────────────────────┘
```

### 🎯 Key Design Principles (From Pipecat & LiveKit)

| Principle | Description | Your Jarvis Status |
|-----------|-------------|-------------------|
| **Voice-First** | Audio as first-class citizen | ✅ Already doing |
| **Pluggable** | Swap STT/LLM/TTS easily | ⚠️ Partially |
| **Composable** | Build from modular components | ⚠️ Needs refactor |
| **Real-Time** | Ultra-low latency (<500ms) | ⚠️ TTS pooling helps |
| **Stateful** | Maintain conversation context | ⚠️ Basic memory |

---

## 2. Core Concepts

### 📦 LiveKit Agents Architecture

```python
# The 4 Core Components:

class Agent:
    """
    An LLM-based application with defined instructions.
    Think of it as the "brain" with personality.
    """
    instructions: str          # System prompt
    tools: List[Tool]         # Available functions
    llm: LLM                  # Language model

class AgentSession:
    """
    Container for agents that manages interactions.
    Handles VAD, STT, TTS orchestration.
    """
    vad: VAD                  # Voice Activity Detection
    stt: STT                  # Speech-to-Text
    llm: LLM                  # Language Model
    tts: TTS                  # Text-to-Speech

class entrypoint:
    """
    Starting point for interactive session.
    Like a request handler in a web server.
    """
    async def handle(ctx: JobContext):
        session = AgentSession(...)
        agent = Agent(instructions="...")
        await session.start(agent=agent)

class AgentServer:
    """
    Main process that coordinates job scheduling.
    Launches agents for user sessions.
    """
    @rtc_session()
    async def entrypoint(ctx: JobContext):
        ...
```

### 📈 Compare with Your Current Jarvis

| Component | LiveKit Style | Your Current Jarvis | Improvement |
|-----------|---------------|---------------------|-------------|
| Agent | `Agent` class | `JarvisAgent` in agent.py | ✅ Similar |
| Session | `AgentSession` | `HybridJarvis` | 🔄 Too monolithic |
| VAD | `silero.VAD` | OpenWakeWord | ✅ Good |
| Routing | `on_enter()` hooks | `QueryRouter` | 🔄 Can improve |
| Tools | `@function_tool` | Plugin system | ✅ Good |

---

## 3. Building Blocks

### 🔧 Block 1: The Agent Class

**Reference: LiveKit Agents**

```python
from livekit.agents import Agent, function_tool, RunContext

class JarvisAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are Jarvis, an intelligent voice assistant.
            
            [Personality]
            - Helpful, professional, slightly witty
            - Concise responses (voice-friendly)
            - Proactive suggestions when appropriate
            
            [Context]
            - User Location: 菏泽, 山东
            - Current Time: {current_time}
            
            [Rules]
            1. Use tools when available
            2. Keep responses under 3 sentences for simple queries
            3. Ask for clarification if ambiguous
            """,
            tools=[
                self.get_weather,
                self.play_music,
                self.get_time,
            ]
        )
    
    @function_tool
    async def get_weather(
        self, 
        context: RunContext,
        location: str = None
    ):
        """
        Get current weather for a location.
        Args:
            location: City name (default: user's location)
        """
        location = location or context.userdata.location
        # Call weather API
        return {"weather": "sunny", "temp": 15}
    
    @function_tool
    async def play_music(
        self,
        context: RunContext,
        query: str,
        action: str = "play"
    ):
        """
        Play or control music.
        Args:
            query: Song name or artist
            action: play, pause, stop, next
        """
        # Call music service
        return {"status": "playing", "song": query}
```

### 🔧 Block 2: The Session Manager

**Reference: Pipecat Pipeline**

```python
class JarvisSession:
    """
    Manages a single conversation session.
    Orchestrates VAD → STT → Agent → TTS flow.
    """
    
    def __init__(self):
        # Components
        self.vad = SileroVAD()
        self.stt = DoubaoSTT()
        self.agent = JarvisAgent()
        self.tts = DoubaoTTS()
        
        # State
        self.is_speaking = False
        self.is_listening = True
        self.context = ConversationContext()
        
        # Queues (Pipecat style)
        self.audio_in_queue = asyncio.Queue()
        self.text_queue = asyncio.Queue()
        self.audio_out_queue = asyncio.Queue()
    
    async def start(self):
        """Start the pipeline"""
        await asyncio.gather(
            self._vad_loop(),
            self._stt_loop(),
            self._agent_loop(),
            self._tts_loop(),
            self._playback_loop(),
        )
    
    async def _vad_loop(self):
        """Voice Activity Detection"""
        while True:
            audio_chunk = await self.audio_in_queue.get()
            
            if self.vad.is_speech(audio_chunk):
                # User is speaking
                self._handle_user_speaking()
            elif self.vad.is_silence(audio_chunk):
                # User stopped speaking
                if self._speech_buffer:
                    await self._finalize_speech()
    
    async def _agent_loop(self):
        """Process user input through agent"""
        while True:
            user_text = await self.text_queue.get()
            
            # Generate response
            async for chunk in self.agent.generate(user_text):
                await self.audio_out_queue.put(await self.tts.synthesize(chunk))
```

### 🔧 Block 3: The Tool System

**Reference: LiveKit function_tool**

```python
from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable

def function_tool(func):
    """
    Decorator to convert a function into a tool.
    Automatically extracts docstring and type hints.
    """
    import inspect
    
    # Extract metadata
    sig = inspect.signature(func)
    doc = func.__doc__ or ""
    
    # Parse docstring for description
    lines = doc.strip().split('\n')
    description = lines[0] if lines else func.__name__
    
    # Build parameters from type hints
    parameters = {}
    for name, param in sig.parameters.items():
        if name in ['self', 'context']:
            continue
        parameters[name] = {
            "type": str(param.annotation.__name__) if param.annotation != inspect.Parameter.empty else "string",
            "required": param.default == inspect.Parameter.empty
        }
    
    # Create tool
    tool = Tool(
        name=func.__name__,
        description=description,
        parameters=parameters,
        handler=func
    )
    
    func._tool = tool
    return func
```

---

## 4. Implementation Guide

### Step 1: Refactor Your Current Jarvis

**Current Problem:** `hybrid_jarvis.py` is 2600+ lines doing everything.

**Solution:** Split into modular components:

```
jarvis_assistant/
├── core/
│   ├── agent.py           # JarvisAgent class (brain)
│   ├── session.py         # JarvisSession (orchestrator)  ← NEW
│   ├── pipeline.py        # Audio pipeline management     ← NEW
│   └── router.py          # Intent routing (simplified)
├── components/
│   ├── vad.py             # Voice Activity Detection      ← NEW
│   ├── stt.py             # Speech-to-Text wrapper        ← NEW
│   ├── tts.py             # Text-to-Speech wrapper        ← NEW
│   └── aec.py             # Echo cancellation
├── tools/
│   ├── weather.py
│   ├── music.py
│   └── ...
└── main.py                # Entry point                   ← NEW
```

### Step 2: Create Clean Entry Point

**New file: `main.py`**

```python
#!/usr/bin/env python3
"""
Jarvis Voice Assistant - Clean Entry Point
Based on LiveKit Agents architecture
"""

import asyncio
from jarvis_assistant.core.session import JarvisSession
from jarvis_assistant.core.agent import JarvisAgent
from jarvis_assistant.utils.audio_utils import play_boot_sound

async def main():
    # Boot sequence
    play_boot_sound()
    
    # Create agent
    agent = JarvisAgent()
    
    # Create session
    session = JarvisSession(
        agent=agent,
        stt_provider="doubao",
        tts_provider="doubao",
        vad_provider="silero"
    )
    
    print("🎙️ Jarvis is ready. Speak or type!")
    
    # Run session
    try:
        await session.start()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    finally:
        await session.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 3: Create Session Class

**New file: `core/session.py`**

```python
"""
JarvisSession - Orchestrates the voice AI pipeline
Based on Pipecat's composable pipeline design
"""

import asyncio
from typing import Optional
from dataclasses import dataclass, field

@dataclass
class SessionConfig:
    """Session configuration"""
    sample_rate: int = 16000
    vad_threshold: float = 0.5
    silence_timeout: float = 1.5
    max_tokens: int = 150

class JarvisSession:
    """
    Manages a single conversation session.
    Handles the flow: Audio → VAD → STT → Agent → TTS → Audio
    """
    
    def __init__(
        self,
        agent,
        stt_provider: str = "doubao",
        tts_provider: str = "doubao",
        vad_provider: str = "silero",
        config: SessionConfig = None
    ):
        self.agent = agent
        self.config = config or SessionConfig()
        
        # State
        self._is_running = False
        self._is_speaking = False
        self._is_processing = False
        self._lock = asyncio.Lock()
        
        # Queues
        self._audio_in = asyncio.Queue(maxsize=100)
        self._audio_out = asyncio.Queue(maxsize=100)
        self._text_in = asyncio.Queue()
        
        # Components (lazy loaded)
        self._vad = None
        self._stt = None
        self._tts = None
        self._speaker = None
        self._mic = None
    
    async def start(self):
        """Start the session pipeline"""
        self._is_running = True
        
        # Initialize components
        await self._init_components()
        
        # Start pipeline tasks
        await asyncio.gather(
            self._mic_reader_task(),
            self._vad_task(),
            self._stt_task(),
            self._agent_task(),
            self._tts_task(),
            self._speaker_task(),
        )
    
    async def stop(self):
        """Stop the session"""
        self._is_running = False
    
    async def _agent_task(self):
        """
        Process text through agent.
        This is the BRAIN of the system.
        """
        while self._is_running:
            try:
                # Get user input
                user_text = await asyncio.wait_for(
                    self._text_in.get(),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                continue
            
            # Skip if already processing
            async with self._lock:
                if self._is_processing:
                    print(f"⚠️ Skipping (busy): {user_text}")
                    continue
                self._is_processing = True
            
            try:
                print(f"🧠 Processing: {user_text}")
                
                # Generate response via agent
                async for chunk in self.agent.generate(user_text):
                    # Stream to TTS
                    audio = await self._tts.synthesize(chunk)
                    await self._audio_out.put(audio)
                
            finally:
                self._is_processing = False
    
    # ... other tasks
```

### Step 4: Improve Agent with Structured Tools

**Update: `core/agent.py`**

```python
"""
JarvisAgent - The intelligent brain
Based on LiveKit multi-agent patterns
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class UserContext:
    """User context across conversations"""
    name: str = "User"
    location: str = "菏泽, 山东"
    preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict] = field(default_factory=list)

class JarvisAgent:
    """
    Jarvis - Your intelligent voice assistant.
    
    Features:
    - Tool calling with structured outputs
    - Conversation memory
    - Context-aware responses
    - Multi-turn reasoning
    """
    
    DEFAULT_INSTRUCTIONS = """
    You are Jarvis, an intelligent voice assistant.
    
    [Personality]
    - Helpful, professional, with subtle wit
    - Concise for voice (max 2-3 sentences for simple queries)
    - Proactive when appropriate
    
    [User Context]
    - Name: {user_name}
    - Location: {user_location}
    - Current Time: {current_time}
    
    [Available Tools]
    {tool_list}
    
    [Rules]
    1. Use tools when they can help
    2. Don't guess - use tools for facts
    3. Ask for clarification if ambiguous
    4. Speak naturally, not robotically
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client or self._get_default_llm()
        self.tools = self._load_tools()
        self.user_context = UserContext()
        
        # Load persistent memory
        self._load_memory()
    
    def _load_tools(self) -> Dict[str, 'Tool']:
        """Load all available tools"""
        from jarvis_assistant.utils import get_plugin_manager
        pm = get_plugin_manager()
        return pm.loaded_plugins
    
    def _get_system_prompt(self) -> str:
        """Generate dynamic system prompt"""
        from datetime import datetime
        
        tool_list = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in self.tools.items()
        ])
        
        return self.DEFAULT_INSTRUCTIONS.format(
            user_name=self.user_context.name,
            user_location=self.user_context.location,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
            tool_list=tool_list
        )
    
    async def generate(self, user_input: str):
        """
        Generate response with tool calling.
        Yields text chunks for streaming TTS.
        """
        # Add to history
        self.user_context.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Build messages
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            *self.user_context.conversation_history[-10:]  # Last 10 turns
        ]
        
        # Call LLM with tools
        response = await self.llm.chat(
            messages=messages,
            tools=self._get_tool_schemas(),
            stream=True
        )
        
        full_response = ""
        
        async for chunk in response:
            # Handle tool calls
            if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                for tool_call in chunk.tool_calls:
                    result = await self._execute_tool(tool_call)
                    # Continue generation with tool result
                    # ...
            
            # Handle text
            if hasattr(chunk, 'content') and chunk.content:
                full_response += chunk.content
                yield chunk.content
        
        # Save to history
        self.user_context.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })
    
    async def _execute_tool(self, tool_call) -> str:
        """Execute a tool and return result"""
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            result = await tool.execute(**tool_args)
            return result
        else:
            return f"Tool '{tool_name}' not found"
```

---

## 5. Improving Your Current Jarvis

### 🔴 Critical Issues to Fix

#### Issue 1: Monolithic hybrid_jarvis.py
**Current:** 2600+ lines, everything in one file
**Fix:** Split into Session, Pipeline, Components

#### Issue 2: Concurrency Bugs
**Current:** `_mark_turn_done` and `on_text_received` race condition
**Fix:** Use proper async locks (already added)

```python
# Good pattern (LiveKit style)
async with self._processing_lock:
    try:
        self.is_processing = True
        await self._process(text)
    finally:
        self.is_processing = False
```

#### Issue 3: No User Context
**Current:** Agent doesn't know user location
**Fix:** Inject context into system prompt

```python
# In agent.py
self.user_context = UserContext(
    name="User",
    location=os.environ.get("JARVIS_LOCATION", "菏泽, 山东")
)

# In system prompt
f"User Location: {self.user_context.location}"
```

### 🟡 Medium Priority Improvements

#### Improvement 1: Semantic Turn Detection
**Reference:** LiveKit's transformer-based turn detection

```python
class SemanticTurnDetector:
    """
    Detect when user finished speaking using ML.
    Better than simple silence detection.
    """
    def __init__(self):
        # Load small transformer model
        self.model = load_turn_detector_model()
    
    def is_turn_complete(self, text: str, audio_features: dict) -> bool:
        """
        Returns True if user likely finished their turn.
        Considers:
        - Sentence completion
        - Question marks
        - Pause duration
        - Prosody (pitch drop)
        """
        features = {
            "text": text,
            "pause_ms": audio_features.get("pause_ms", 0),
            "pitch_drop": audio_features.get("pitch_drop", False)
        }
        return self.model.predict(features) > 0.7
```

#### Improvement 2: Streaming Response
**Reference:** Pipecat's streaming pipeline

```python
async def _speak_streaming(self, text_stream):
    """
    Stream TTS as text is generated.
    Don't wait for full response.
    """
    buffer = ""
    
    async for chunk in text_stream:
        buffer += chunk
        
        # Flush on punctuation
        if any(p in chunk for p in "。！？，.!?,"):
            audio = await self.tts.synthesize(buffer)
            await self.audio_out.put(audio)
            buffer = ""
    
    # Final flush
    if buffer:
        audio = await self.tts.synthesize(buffer)
        await self.audio_out.put(audio)
```

### 🟢 Nice-to-Have Features

#### Feature 1: Multi-Agent Handoff
**Reference:** LiveKit's multi-agent example

```python
class IntroAgent(Agent):
    """First agent - gathers user info"""
    
    @function_tool
    async def handoff_to_task_agent(self, task_type: str):
        """Hand off to specialized agent"""
        if task_type == "weather":
            return WeatherAgent(), "Let me check the weather for you."
        elif task_type == "music":
            return MusicAgent(), "I'll help you with music."
        else:
            return GeneralAgent(), "Let me help you with that."

class WeatherAgent(Agent):
    """Specialized weather agent"""
    instructions = "You are a weather expert..."
```

#### Feature 2: Interruption Handling
**Reference:** Pipecat's interruption detection

```python
async def _handle_interruption(self):
    """
    Handle user interrupting Jarvis.
    Stop TTS immediately and listen.
    """
    # Clear audio queue
    while not self.audio_out.empty():
        self.audio_out.get_nowait()
    
    # Stop current TTS
    await self.tts.stop()
    
    # Flag for agent
    self.was_interrupted = True
    
    print("🤫 User interrupted, listening...")
```

---

## 6. Advanced Patterns

### Pattern 1: The Sandwich Architecture (LangChain)

```
┌─────────────────────────────────────┐
│           STT LAYER                 │
│   (Speech → Text, fast streaming)  │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│           AGENT LAYER               │
│   (Text → Text, reasoning/tools)   │
│   • Intent classification          │
│   • Tool execution                 │
│   • Response generation            │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│           TTS LAYER                 │
│   (Text → Speech, streaming)       │
└─────────────────────────────────────┘
```

### Pattern 2: Event-Driven Architecture

```python
class EventBus:
    """Central event bus for loose coupling"""
    
    def __init__(self):
        self._handlers = {}
    
    def on(self, event: str, handler: Callable):
        self._handlers.setdefault(event, []).append(handler)
    
    async def emit(self, event: str, data: Any = None):
        for handler in self._handlers.get(event, []):
            await handler(data)

# Usage
bus = EventBus()

bus.on("user_speech_end", agent.process)
bus.on("agent_response", tts.synthesize)
bus.on("audio_ready", speaker.play)
bus.on("interruption", lambda: bus.emit("stop_tts"))
```

### Pattern 3: Pipeline Composition

```python
class Pipeline:
    """Composable audio pipeline"""
    
    def __init__(self):
        self.stages = []
    
    def add(self, stage: 'PipelineStage') -> 'Pipeline':
        self.stages.append(stage)
        return self
    
    async def process(self, input_data):
        data = input_data
        for stage in self.stages:
            data = await stage.process(data)
        return data

# Usage
pipeline = (
    Pipeline()
    .add(NoiseFilter())
    .add(EchoCancellation())
    .add(VAD())
    .add(STT())
    .add(IntentRouter())
    .add(Agent())
    .add(TTS())
)
```

---

## 7. UX Best Practices

### 🎯 Voice-First Design Rules

1. **Keep it Short**
   - ❌ "The current weather in Heze, Shandong, China is partly cloudy with a temperature of 15 degrees Celsius, humidity at 45%, and wind speed of 10 kilometers per hour."
   - ✅ "菏泽现在多云，15度。"

2. **Acknowledge Immediately**
   - Play a sound or say "好的" within 200ms
   - Don't leave user wondering if you heard them

3. **Handle Errors Gracefully**
   - ❌ "Error: API timeout"
   - ✅ "抱歉，网络有点慢。再说一次？"

4. **Be Proactive**
   - ✅ "早上好！今天菏泽有雨，记得带伞。"

5. **Maintain Context**
   - User: "明天呢？"
   - ✅ (Remembers they asked about weather) "明天多云，18度。"

---

## 📋 Action Items for Your Jarvis

### Phase 1: Stabilization (This Week)
- [x] Fix concurrency bugs
- [x] Fix boot sound
- [ ] Add user location to system prompt
- [ ] Test S2S suppression

### Phase 2: Refactoring (Next Week)
- [ ] Extract Session class from hybrid_jarvis.py
- [ ] Create Pipeline abstraction
- [ ] Improve Agent system prompt

### Phase 3: Enhancement (Week After)
- [ ] Add semantic turn detection
- [ ] Implement streaming response
- [ ] Add interruption handling

### Phase 4: Advanced (Future)
- [ ] Multi-agent architecture
- [ ] Voice emotion detection
- [ ] Proactive suggestions

---

## 🔗 Reference Repositories

| Project | GitHub | Best For |
|---------|--------|----------|
| **Pipecat** | pipecat-ai/pipecat | Pipeline design |
| **LiveKit Agents** | livekit/agents | Agent architecture |
| **LangGraph Voice** | kenneth-liao/langgraph-voice-agent | LLM integration |
| **OpenAI Realtime** | openai/openai-realtime-api-beta | Low latency |

---

## 💡 Key Takeaways

1. **Modular > Monolithic**: Split your code into small, testable pieces
2. **Async Everywhere**: Voice AI is inherently async, embrace it
3. **Lock Your State**: Concurrency bugs are the #1 enemy
4. **Context is King**: User context makes responses 10x better
5. **Stream Everything**: Don't wait for full responses, stream ASAP

---

*Happy Building! 🚀*
