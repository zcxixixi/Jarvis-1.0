# Jarvis V2 - Modular Voice AI Assistant

Complete restructuring of the original 2682-line `hybrid_jarvis.py` into clean, testable modules.

## 🎯 Goals

- ✅ **Modular**: Each component < 300 lines
- ✅ **Testable**: Every module has independent tests
- ✅ **Reusable**: Components can be used in other projects
- ✅ **Open-Source**: Uses battle-tested libraries (Pipecat, Silero, etc.)
- ✅ **Debuggable**: Easy to find and fix bugs

## 📦 Architecture

```
jarvis_v2/
├── config.py              # Centralized configuration
├── components/            # Reusable components
│   ├── audio_io.py       # PyAudio wrapper (200 lines)
│   ├── vad.py            # Voice Activity Detection
│   ├── wake_word.py      # Wake word detection
│   ├── stt.py            # Speech-to-Text
│   └── tts.py            # Text-to-Speech with pooling
├── pipeline/              # Pipecat-style pipeline
│   └── voice_pipeline.py
├── agent/                 # AI agent logic
│   └── jarvis_agent.py
├── session/               # Session management
│   └── session.py        # Main orchestrator
└── tests/                 # Module tests
    ├── test_audio_io.py
    ├── test_vad.py
    └── ...
```

## 🚀 Quick Start

### Installation

```bash
cd jarvis_v2

# Install dependencies
pip install -r requirements.txt

# Test individual module
python tests/test_audio_io_simple.py
```

### Run Tests

```bash
# Test all modules
python -m pytest tests/ -v

# Test specific module
python tests/test_audio_io_simple.py
```

## 📚 Module Overview

### 1. AudioIO (`components/audio_io.py`)
- Handles microphone and speaker
- Async read/write interface
- Thread-safe queues
- Volume detection

**Usage:**
```python
from jarvis_v2.components.audio_io import AudioIO

audio = AudioIO()
await audio.start()

# Read from mic
async for chunk in audio.read_stream():
    process(chunk)

# Write to speaker
await audio.write(audio_data)
```

### 2. VAD (`components/vad.py`)
- Voice Activity Detection using Silero
- Detects speech vs silence
- Speech timestamp extraction

### 3. Wake Word (`components/wake_word.py`)
- Detects "Hey Jarvis"
- Uses OpenWakeWord
- Configurable threshold

### 4. Session (`session/session.py`)
- Orchestrates all components
- Replaces the 2682-line HybridJarvis class
- Clean state machine

### 5. Agent (`agent/jarvis_agent.py`)
- LLM-based reasoning
- Tool calling
- Conversation memory

## 🔄 Migration Status

| Component | Status | Lines | Tested |
|-----------|--------|-------|--------|
| Config | ✅ Done | 100 | ✅ |
| AudioIO | ✅ Done | 250 | ⏳ Testing |
| VAD | ⏳ Next | - | - |
| Wake Word | ⏳ Next | - | - |
| STT | ⏳ Next | - | - |
| TTS | ⏳ Next | - | - |
| Session | ⏳ Next | - | - |
| Agent | ⏳ Next | - | - |

## 📊 Progress

**Before:**
- One file: 2682 lines
- One class: 67 methods
- Hard to debug/test/maintain

**After (Target):**
- Main file: ~50 lines
- Largest module: ~300 lines
- 100% test coverage
- Each component testable

## 🤝 Contributing

To add a new module:

1. Create module in appropriate directory
2. Keep it < 300 lines
3. Add tests in `tests/`
4. Document usage in README
5. Update migration status table

## 📝 License

Same as original Jarvis project
