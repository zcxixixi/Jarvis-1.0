# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-02-01

### 🎉 Major Release: Complete Modular Restructuring

#### Changed
- **BREAKING:** Completely restructured from monolithic to modular architecture
- Replaced 2,682-line `hybrid_jarvis.py` with 9 focused modules (~1,020 lines total)
- Renamed STT → ASR throughout codebase for consistency

#### Added
- `jarvis_v2/` - New modular architecture
  - `config.py` - Centralized configuration (100 lines)
  - `components/audio_io.py` - Async audio I/O (250 lines)
  - `components/vad.py` - Voice Activity Detection (150 lines)
  - `components/wake_word.py` - Wake word detection (140 lines)
  - `components/asr.py` - Speech recognition wrapper (80 lines)
  - `components/tts.py` - TTS with connection pooling (100 lines)
  - `agent/jarvis_agent.py` - Agent wrapper (80 lines)
  - `session/session.py` - Main orchestrator (220 lines)
  - `main.py` - Clean entry point (50 lines)
- Module test suite with 8 automated tests
- Clear state machine: IDLE → LISTENING → PROCESSING → SPEAKING
- Comprehensive README documentation

#### Archived
- `archive/old_core/hybrid_jarvis.py` - Original monolithic file
- `archive/old_core/query_router.py` - Original router

#### Benefits
- Each module < 300 lines (avg 130 lines)
- 100% of modules import successfully
- Independent testing for each component
- Much easier to debug and maintain
- AI-friendly: can edit one module at a time

## [1.x.x] - Previous versions

Legacy monolithic architecture in `jarvis_assistant/core/hybrid_jarvis.py`
