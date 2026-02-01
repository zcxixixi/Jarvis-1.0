# Jarvis Development Skill Guide
> **Last Updated**: 2026-02-01 (V2 Modular Architecture)

This document captures verified patterns, lessons learned, and guidelines for future development.

---

## 🧠 Core Architecture (V2)

```
jarvis_v2/
├── main.py              # Entry point
├── config.py            # Centralized settings
├── components/
│   ├── audio_io.py     # PyAudio async wrapper
│   ├── vad.py          # Voice Activity Detection (Silero)
│   ├── wake_word.py    # "Hey Jarvis" detection
│   ├── asr.py          # Speech recognition (Doubao)
│   └── tts.py          # Text-to-Speech (Doubao V3)
├── agent/
│   └── jarvis_agent.py # LangGraph agent wrapper
└── session/
    └── session.py      # Main state machine orchestrator
```

**State Machine:**
```
IDLE → (wake word) → LISTENING → (silence) → PROCESSING → (response) → SPEAKING → IDLE
```

---

## ⚡ Performance Benchmarks (Verified)

| Metric | Target | Achieved |
|--------|--------|----------|
| LLM TTFT (Time to First Token) | <1s | **0.6s** ✅ |
| Audio TTFB (Time to First Byte) | <2s | **1.2s** ✅ |
| End-to-End (Voice In -> Voice Out) | <3s | **~2s** ✅ |

---

## 🔧 Key Files & Entry Points

| File | Purpose |
|------|---------|
| `jarvis_v2/main.py` | New modular entry point |
| `jarvis_v2/session/session.py` | State machine orchestrator |
| `jarvis_v2/components/asr.py` | Speech recognition |
| `jarvis_v2/components/tts.py` | TTS with connection pooling |
| `jarvis_v2/config.py` | All configuration |
| `jarvis_assistant/services/doubao/tts_v3.py` | TTS WebSocket client |

**Archived (old monolithic):**
| File | New Location |
|------|--------------|
| `hybrid_jarvis.py` | `archive/old_core/` |
| `query_router.py` | `archive/old_core/` |

---

## 🚨 Critical Lessons Learned

### 1. ❌ DO NOT Touch Working TTS/ASR Code
> The WebSocket protocol for Doubao is **fragile**. If it works, leave it alone.
> - `tts_v3.py` yields raw bytes; test scripts must handle `isinstance(result, bytes)`.
> - Session rotation requires `finish_session` + 600ms delay before `start_session`.

### 2. ⚡ Ultra-Low Latency: Use Responses API
```python
# Correct: Use /api/v3/responses with thinking disabled
payload = {
    "model": endpoint_id,
    "input": [...],
    "stream": True,
    "thinking": {"type": "disabled"}  # <-- 90% latency reduction!
}
```
- The Chat Completions API (`/api/v3/chat/completions`) is **slower**.
- `thinking: disabled` cuts TTFT from 6s to 0.6s.

### 3. 🔤 Text Cleaning for TTS
Emoji and special characters crash TTS. Always clean text:
```python
from jarvis_assistant.utils.text_utils import clean_text_for_tts
cleaned = clean_text_for_tts("Hello 😂")  # -> "Hello"
```

### 4. 🎵 Music Control Flags
When Agent speaks, music must pause and mic must mute:
- `self.self_speaking_mute = True` (mute mic during TTS)
- `self.skip_cloud_response = True` (suppress S2S audio)
- **Always reset these in a `finally` block.**

---

## 📂 Module Testing

### Run All Module Tests
```bash
cd jarvis_v2
./run_tests.sh
```

### Test Individual Modules
```bash
../venv/bin/python3 tests/test_vad_simple.py
../venv/bin/python3 tests/test_wake_word_simple.py
```

---

## 🧩 Verified Code Patterns

### PyAudio Async Wrapper (V2 Pattern)
From `jarvis_v2/components/audio_io.py`:
```python
audio = AudioIO()
await audio.start()

async for chunk in audio.read_stream():
    volume = audio.get_volume_level(chunk)

await audio.write(audio_data)
```

### VAD with Silero (V2 Pattern)
From `jarvis_v2/components/vad.py`:
```python
vad = VoiceActivityDetector()

for chunk in audio_stream:
    is_speech, event = vad.process_stream(chunk)
    if event == "speech_end":
        process_utterance()
```

### TTS with Connection Pooling (V2 Pattern)
From `jarvis_v2/components/tts.py`:
```python
tts = TTSEngine()  # Singleton

async for audio_chunk in tts.synthesize("你好"):
    await audio.write(audio_chunk)
```

---

## 🎯 Migration Notes (V1 → V2)

| V1 (Old) | V2 (New) |
|----------|----------|
| `hybrid_jarvis.py` (2682 lines) | 9 modules (~1020 lines) |
| `query_router.py` | Simplified in `session.py` |
| STT terminology | ASR terminology |
| Monolithic class | State machine + components |

---

## 🎯 Future Development Roadmap

1. **Integration Completion**:
   - Connect ASR module to real Doubao client
   - Full end-to-end testing

2. **Hardware Optimization**:
   - Profile and optimize for Raspberry Pi 4B
   - Reduce plugin loading time

3. **Multi-Modal Support**:
   - Image input handling
   - Screen capture integration
