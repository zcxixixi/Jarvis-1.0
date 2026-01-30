#!/usr/bin/env python3
"""
Test Doubao V3 TTS output (text -> streaming audio bytes)
Usage: python3 test_doubao_tts_v3.py "你好，先生"
"""
import asyncio
import os
import sys
import wave
from dotenv import load_dotenv

# Project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(PROJECT_ROOT)

# Load env
load_dotenv(os.path.join(PROJECT_ROOT, "jarvis_assistant", ".env"), override=True)

from jarvis_assistant.services.doubao.tts_v3 import synthesize_stream

async def main():
    text = sys.argv[1] if len(sys.argv) > 1 else "你好，先生。我是Jarvis。"
    print(f"Sending text: {text}")
    
    pcm_data = bytearray()
    sr = int(os.getenv("DOUBAO_TTS_SAMPLE_RATE", "24000"))
    
    try:
        async for chunk in synthesize_stream(text):
            print(f"Received chunk: {len(chunk)} bytes")
            pcm_data.extend(chunk)
            
        out_path = "/tmp/doubao_tts_v3.wav"
        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm_data)
        print(f"✅ V3 TTS saved: {out_path} ({len(pcm_data)} bytes)")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
