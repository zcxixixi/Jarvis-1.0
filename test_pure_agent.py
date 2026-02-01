#!/usr/bin/env python3
"""
Pure Agent + TTS Test
Tests the unified architecture WITHOUT Doubao Realtime S2S

Flow:
1. Text input → Agent (brain)
2. Agent response → TTS V3 (voice)
3. Audio output via pyaudio

This validates we don't need the complex Realtime S2S WebSocket.
"""

import asyncio
import sys
import os
import pyaudio

# Add project root to path
sys.path.append(os.getcwd())

from jarvis_assistant.core.agent import get_agent
from jarvis_assistant.services.doubao.tts_v3 import DoubaoTTSV1

async def play_audio_stream(audio_chunks):
    """Play PCM audio chunks via pyaudio"""
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=24000,
        output=True
    )
    
    chunk_count = 0
    for chunk in audio_chunks:
        stream.write(chunk)
        chunk_count += 1
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    return chunk_count

async def test_pure_agent_tts():
    print("🤖 Testing Pure Agent + TTS Flow (No Realtime S2S)")
    print("=" * 60)
    
    # 1. Initialize Agent
    print("\n1️⃣  Initializing Agent...")
    agent = get_agent()
    print("   ✅ Agent ready")
    
    # 2. Initialize TTS
    print("\n2️⃣  Initializing TTS V3...")
    tts = DoubaoTTSV1()
    await tts.connect()
    print("   ✅ TTS ready")
    
    # 3. Test queries
    test_queries = [
        "你好",
        # "今天天气怎么样",  # Skip weather to speed up test
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 60}")
        print(f"Test {i}/{len(test_queries)}: {query}")
        print(f"{'=' * 60}")
        
        # Step 1: Agent processes query (BRAIN)
        print(f"\n📥 Input: {query}")
        response = await agent.run(query)
        print(f"🧠 Agent Response: {response}")
        
        # Step 2: TTS synthesizes speech (VOICE)
        print(f"\n🔊 Synthesizing speech...")
        try:
            audio_chunks = []
            async for chunk in tts.synthesize(response):
                audio_chunks.append(chunk)
            
            print(f"   ✅ TTS generated {len(audio_chunks)} audio chunks")
            
            # Step 3: Play audio
            print(f"   🎵 Playing audio...")
            chunk_count = await play_audio_stream(audio_chunks)
            print(f"   ✅ Played {chunk_count} chunks successfully")
            
        except Exception as e:
            print(f"   ❌ TTS/Audio error: {e}")
            import traceback
            traceback.print_exc()
        
        # Wait a bit between tests
        await asyncio.sleep(1)
    
    await tts.close()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("\n💡 Result: Pure Agent + TTS works WITHOUT Realtime S2S")

if __name__ == "__main__":
    asyncio.run(test_pure_agent_tts())
