# Jarvis - Modular Voice AI Assistant

<div align="center">

**🎤 A modern, modular voice AI assistant built with Python**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

## 🎯 Overview

Jarvis is a voice AI assistant that combines:
- **Wake word detection** ("Hey Jarvis")
- **Voice activity detection** (knows when you're speaking)
- **Speech recognition** (Doubao ASR)
- **AI reasoning** (LangGraph agent with tools)
- **Text-to-speech** (Doubao TTS with connection pooling)

## 🏗️ Architecture

```
jarvis_v2/
├── main.py              # Entry point (50 lines)
├── config.py            # Centralized settings
│
├── components/          # Core components
│   ├── audio_io.py     # PyAudio wrapper (async)
│   ├── vad.py          # Voice Activity Detection
│   ├── wake_word.py    # Wake word detection
│   ├── asr.py          # Speech recognition
│   └── tts.py          # Text-to-speech
│
├── agent/               # AI reasoning
│   └── jarvis_agent.py # LangGraph agent
│
├── session/             # Orchestration
│   └── session.py      # Main state machine
│
└── tests/               # Module tests
    ├── test_vad_simple.py
    └── test_wake_word_simple.py
```

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/your-username/jarvis.git
cd jarvis

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run Jarvis
cd jarvis_v2
python main.py
```

## 📦 Modules

| Module | Description | Lines | Status |
|--------|-------------|-------|--------|
| **AudioIO** | Async mic/speaker I/O | 250 | ✅ |
| **VAD** | Voice activity detection | 150 | ✅ |
| **WakeWord** | "Hey Jarvis" detection | 140 | ✅ |
| **ASR** | Speech recognition | 80 | ✅ |
| **TTS** | Text-to-speech | 100 | ✅ |
| **Agent** | AI reasoning | 80 | ✅ |
| **Session** | State machine | 220 | ✅ |

**Total:** ~1,020 lines (vs 2,682 in old version)

## 🧪 Testing

```bash
cd jarvis_v2

# Run all tests
./run_tests.sh

# Test individual module
../venv/bin/python3 tests/test_vad_simple.py
```

## 🔧 Configuration

Edit `jarvis_v2/config.py`:

```python
@dataclass
class JarvisConfig:
    audio: AudioConfig        # Sample rate, channels
    vad: VADConfig           # Speech detection threshold
    wake_word: WakeWordConfig # Wake phrases
    asr: ASRConfig           # Speech recognition
    tts: TTSConfig           # Voice synthesis
    agent: AgentConfig       # LLM settings
    
    user_location: str = "菏泽, 山东"
    user_name: str = "User"
```

## 🎙️ Supported Wake Words

- "Hey Jarvis"
- "Jarvis"
- "嘿 Jarvis"
- "贾维斯"

## 📋 State Machine

```
IDLE → (wake word) → LISTENING
LISTENING → (silence) → PROCESSING
PROCESSING → (response) → SPEAKING
SPEAKING → (done) → IDLE
```

## 🔌 Dependencies

- **PyAudio** - Audio I/O
- **Torch** - Silero VAD (optional)
- **LangGraph** - Agent orchestration
- **Doubao API** - ASR/TTS

## 📜 License

MIT License - see [LICENSE](LICENSE)

## 🙏 Acknowledgments

- [Pipecat](https://github.com/pipecat-ai/pipecat) - Pipeline architecture inspiration
- [Silero VAD](https://github.com/snakers4/silero-vad) - Voice activity detection
- [OpenWakeWord](https://github.com/dscripka/openWakeWord) - Wake word detection
