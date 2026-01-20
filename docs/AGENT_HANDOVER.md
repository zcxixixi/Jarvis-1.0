# Jarvis Project Handover & Resume Guide

This document provides essential information for an AI agent to resume work on the Jarvis project.

## 1. Connection Details
- **Target Device**: Raspberry Pi 4/5
- **IP Address**: `192.168.31.150`
- **Username**: `shumeipai`
- **Authentication**: SSH key-based (passwordless) from this Mac is already configured. 
- **Workspace**: `~/jarvis-assistant`

## 2. Bluetooth Speaker (小爱音箱-5134)
The speaker needs to be paired/connected after a reboot.
- **MAC Address**: `8C:53:C3:23:48:B4`
- **Automation Script**: Use `bt_pair.exp` (expect script) located in the project root.
- **Command**: `expect bt_pair.exp` (Run this on the Pi to force re-pairing/connection).

## 3. Environment & Running
- **Python Environment**: `python3` (v3.13) on Pi.
- **Dependencies**: `python-miio`, `pyaudio`, `websockets`, `speechrecognition` are already installed.
- **Core Script**: `hybrid_jarvis.py` (Main application).
- **Latency Testing**: `test_doubao_audio_file.py` (Optimized parallel streaming at 24kHz).
- **Configuration**: API keys and model settings are in `.env` and `jarvis_doubao_config.py`.

## 4. Current Progress & Next Steps
- [x] Deployment finished.
- [x] SSH Passwordless setup complete.
- [x] Bluetooth audio optimized at 24kHz.
- [x] Parallel streaming pipeline verified (low latency).
- [ ] **Next Step**: Connect USB Microphone and update `MICROPHONE_DEVICE_INDEX` in `.env`.
- [ ] **Next Step**: Integrate Mi Home (MiJia) via `python-miio` for device control.

## 5. Helpful Commands
- **Check Audio Devices**: `arecord -l` (input) and `aplay -l` (output).
- **Test Bluetooth Sound**: `speaker-test -t wav -c 1` or `ffplay test_input.wav`.
- **Git Backup**: `git push origin main` (Syncs local Mac changes to GitHub).
