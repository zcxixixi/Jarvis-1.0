#!/usr/bin/env python3
"""
Test streaming output and latency optimization.
Demonstrates <1s first token target for voice UX.
"""

import asyncio
import time
from jarvis_assistant.io.text import ConsoleOutput


async def simulate_llm_stream():
    """Simulate LLM generating response in chunks."""
    response = "Hello! I'm demonstrating streaming output for low latency voice UX."
    words = response.split()
    
    for word in words:
        yield word + " "
        await asyncio.sleep(0.1)  # Simulate generation delay


async def test_streaming_latency():
    """Test streaming output latency."""
    print("🧪 Testing Streaming Latency")
    print("=" * 60)
    
    output = ConsoleOutput(prefix="Jarvis: ", enable_streaming_demo=True)
    
    # Test 1: Acknowledgment (instant feedback)
    print("\n📍 Test 1: Instant Acknowledgment")
    t0 = time.time()
    await output.play_acknowledgment()
    t_ack = (time.time() - t0) * 1000
    print(f"   Latency: {t_ack:.1f}ms {'✅' if t_ack < 100 else '❌'}")
    
    # Test 2: Streaming response
    print("\n📍 Test 2: Streaming Response")
    print("   (First chunk should appear immediately)\n")
    
    t0 = time.time()
    first_chunk_time = None
    
    async def tracked_stream():
        nonlocal first_chunk_time
        chunk_num = 0
        async for chunk in simulate_llm_stream():
            chunk_num += 1
            if chunk_num == 1:
                first_chunk_time = (time.time() - t0) * 1000
            yield chunk
    
    await output.speak_stream(tracked_stream())
    total_time = (time.time() - t0) * 1000
    
    print(f"\n   First chunk: {first_chunk_time:.0f}ms {'✅' if first_chunk_time < 1000 else '❌'}")
    print(f"   Total time: {total_time:.0f}ms")
    
    # Test 3: Non-streaming (for comparison)
    print("\n📍 Test 3: Non-Streaming (for comparison)")
    t0 = time.time()
    await output.speak("Hello! I'm a complete response (not streamed).")
    non_streaming_time = (time.time() - t0) * 1000
    print(f"   Latency: {non_streaming_time:.0f}ms")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"   Acknowledgment:   {t_ack:.0f}ms (target: <100ms)")
    print(f"   First chunk:      {first_chunk_time:.0f}ms (target: <1000ms)")
    print(f"   Non-streaming:    {non_streaming_time:.0f}ms")
    print(f"\n   Improvement: {non_streaming_time / first_chunk_time:.1f}x faster to first output!")


if __name__ == "__main__":
    asyncio.run(test_streaming_latency())
