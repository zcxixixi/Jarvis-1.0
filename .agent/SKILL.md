# Jarvis Development Skill Guide
> **Last Updated**: 2026-01-31

This document captures verified patterns, lessons learned, and guidelines for future development.

---

## 🧠 Core Architecture

```
[1. Wake Word] -> [2. ASR (Doubao Realtime)] -> [3. Router] -> [4. Agent] -> [5. TTS V3] -> [6. Speaker]
```

- **ASR**: Uses Doubao Realtime Dialog API (WebSocket, Binary Protocol)
- **Agent**: `JarvisAgent` with streaming callback support
- **TTS**: Doubao TTS V3 (Binary WebSocket, NOT HTTP)
- **Router**: `QueryRouter` decides between S2S (simple) and Agent (complex) paths

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
| `main.py` | CLI entry for quick agent tests |
| `jarvis_assistant/core/hybrid_jarvis.py` | Main voice assistant loop |
| `jarvis_assistant/core/agent.py` | LLM planning & tool execution |
| `jarvis_assistant/core/query_router.py` | Intent routing (S2S vs Agent) |
| `jarvis_assistant/services/doubao/tts_v3.py` | TTS WebSocket client |
| `test_full_voice_pipeline.py` | **E2E test** (LLM -> TTS -> Audio) |

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

## 📂 Test Script Reference

### `test_full_voice_pipeline.py`
**Purpose**: End-to-end test from LLM text generation to audio playback.
**Usage**: `./venv/bin/python3 test_full_voice_pipeline.py`
**What it verifies**:
- LLM streaming works
- TTS can synthesize Chinese text
- PyAudio can play the output

## 🧩 Verified Code Patterns

### PyAudio Streaming Playback
Used in `test_full_voice_pipeline.py` to play raw PCM bytes from TTS V3:
```python
import pyaudio
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)

# Play chunks as they arrive from WebSocket
async for chunk in tts.synthesize(text):
    if isinstance(chunk, bytes):
        stream.write(chunk)
```

### Punctuation-based Text Buffering
Used to ensure natural pauses and stop emoji-related TTS crashes:
```python
buffer = ""
for token in llm_stream:
    buffer += token
    if any(p in token for p in "，。！？,.!?\n"):
        cleaned = clean_text_for_tts(buffer)
        if cleaned:
            await tts.synthesize(cleaned)
        buffer = ""
```

---

## 🎯 Future Development Roadmap

1. **Clawdbot-Inspired Enhancements**:
   - `MEMORY.md` for transparent, editable long-term memory
   - `SOUL.md`-style persona prompts
   - "Heartbeat" proactive mechanism

2. **Hardware Optimization**:
   - Profile and optimize for Raspberry Pi 4B
   - Reduce plugin loading time

3. **Multi-Modal Support**:
   - Image input handling
   - Screen capture integration
