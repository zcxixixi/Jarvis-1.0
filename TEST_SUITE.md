# Jarvis Test Suite

## Quick Access Guide

### ✅ Recommended Tests to Keep

#### End-to-End Test
- **`test_e2e_pipeline.py`** (Root) - Complete ASR→Intent→Agent→TTS pipeline test

#### TTS Tests
- **`scripts/test_tts_module.py`** - TTS V3 module test
- **`scripts/test_tts_expressive.py`** - Expressive voice test
- **`jarvis_assistant/tests/test_doubao_tts_v3.py`** - TTS V3 detailed test
- **`jarvis_assistant/tests/test_tts_bidir.py`** - Bidirectional TTS test

#### ASR Tests
- **`jarvis_assistant/tests/test_asr_hook.py`** - ASR hook test

#### Integration Tests
- **`jarvis_assistant/tests/test_robustness.py`** - System robustness
- **`jarvis_assistant/tests/test_connection.py`** - Connection stability
- **`jarvis_assistant/tests/test_audio_latency.py`** - Latency monitoring

#### Tool Tests
- **`scripts/test_weather_news.py`** - Weather/news tools
- **`scripts/test_yfinance.py`** - Stock tools

---

## Usage (with correct environment)

### From VS Code (✅ Recommended)
1. Open any test file
2. Click ▶️ Run button (top right)
3. Or press `Ctrl+F5`

### From Terminal
```bash
cd /Users/kaijimima1234/Desktop/jarvis

# End-to-End
./venv/bin/python3 test_e2e_pipeline.py

# TTS
./venv/bin/python3 scripts/test_tts_module.py

# ASR  
./venv/bin/python3 jarvis_assistant/tests/test_asr_hook.py

# Full system (with wake word)
./venv/bin/python3 main.py
```

---

## ❌ Tests to Delete (Obsolete/Failed)

### Debug Scripts (V3 protocol already working)
```bash
cd jarvis_assistant/tests
rm -f check_v*.py dialogue_auto_check.py doubao_http_check.py soak_test.py
```

### Duplicate/Outdated Tests
```bash
cd jarvis_assistant/tests
rm -f test_doubao_audio_file.py test_doubao_tts_http.py test_doubao_tts_text.py \
      test_edge_cases.py test_functional_perfections.py test_headless.py \
      test_hybrid_top.py test_learning.py test_minimal.py \
      test_network_down.py test_pipeline.py test_realtime_*.py \
      test_resilience.py test_v3_http.py test_real_v3.py
```

---

## VS Code Setup

The `.vscode/settings.json` has been configured to use the correct virtual environment:
- Path: `/Users/kaijimima1234/Desktop/jarvis/venv/bin/python3`
- All dependencies are installed there

**Restart VS Code** to apply the settings.
