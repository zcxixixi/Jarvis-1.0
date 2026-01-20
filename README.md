# Jarvis Assistant

A hyper-optimized, hybrid AI assistant for Raspberry Pi (and Mac).
Combines **Doubao Realtime API** (for natural conversation) with **Local Tools** (for fast home control).

## 🚀 Quick Start
```bash
./start.sh
```

## 🛠️ Debugging & Verification Tools (New!)
We have added a suite of professional tools to verify every aspect of the system.

### 1. Audio & AEC
- **Test Echo Cancellation**: `./test_aec.sh` (Select Music/Speech/Sweep modes)
- **Test Noise Suppression**: `./test_noise.sh`
- **Calibrate Latency**: `./calibrate.sh` (Crucial for perfect AEC)

### 2. Logic & Connectivity
- **Test Cloud Connection**: `./test_api.sh`
- **Test Intent Logic**: `python3 tests/test_intents.py`
- **Test Flow Logic**: `python3 tests/test_flow_simulation.py`

## 📁 System Structure
- **`hybrid_jarvis.py`**: Main application entry point.
- **`aec_processor.py`**: Software Acoustic Echo Cancellation.
- **`tests/`**: All verification scripts.
- **`tools/`**: Local capabilities (Music, Weather, etc).
