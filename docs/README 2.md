# Jarvis 1.0 - AI Voice Assistant

A real-time voice assistant powered by ByteDance Doubao API, featuring continuous conversation, music playback, and smart home control.

## Features

- 🎙️ **Real-time Voice Interaction** - Full-duplex conversation with <1s latency
- 🗣️ **Continuous Dialogue** - 15-second conversation window, no need to repeat wake word
- 🎵 **Music Playback** - Netease Cloud Music (VIP bypass) with automatic fallback
- 🏠 **Smart Home** - Xiaomi/Mi Home device control
- 🎤 **Wake Word** - Offline "Jarvis" detection via Porcupine
- 🔇 **Echo Suppression** - Auto-mute during playback to prevent feedback

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run Jarvis
python3 hybrid_jarvis.py
```

## Voice Commands

- **Wake**: Say "Jarvis" to activate
- **Music**: "播放周杰伦的歌" / "停止播放" / "暂停"
- **Weather**: "今天天气怎么样"
- **Sleep**: "退下" / "休息吧"

## Configuration

Edit `jarvis_doubao_config.py` to configure:
- Doubao API credentials
- TTS voice selection
- Jarvis persona

## License

MIT
