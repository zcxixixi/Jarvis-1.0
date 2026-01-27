#!/usr/bin/env python3
"""
Test Doubao Realtime ASR Extraction
Run this to see if we can capture user text events.
"""
import asyncio
import jarvis_doubao_config as config
from jarvis_doubao_realtime import DoubaoRealtimeJarvis

class MockJarvis(DoubaoRealtimeJarvis):
    async def on_text_received(self, text: str):
        print(f"\n✅ CAPTURED ASR: [{text}]")

async def main():
    print("🎤 Please speak into the microphone (Ctrl+C to stop)...")
    j = MockJarvis()
    await j.connect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped")
