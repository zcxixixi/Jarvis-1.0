#!/usr/bin/env python3
"""
Test REAL Doubao LLM streaming with latency measurement.
This tests the actual API, not simulation.
"""

import asyncio
import time
import os
from jarvis_assistant.agent import JarvisAgent
from jarvis_assistant.io.text import ConsoleOutput


async def test_real_llm_streaming():
    """Test real Doubao LLM streaming latency."""
    print("🧪 Testing REAL Doubao LLM Streaming")
    print("=" * 60)
    
    # Check credentials
    if not os.getenv("DOUBAO_ACCESS_TOKEN"):
        print("❌ ERROR: DOUBAO_ACCESS_TOKEN not set!")
        print("   Please set environment variable and try again.")
        return
    
    # Create agent with streaming
    agent = JarvisAgent(session_id="llm_test", enable_streaming=True)
    output = ConsoleOutput(prefix="Jarvis: ", enable_streaming_demo=False)
    
    # Test queries
    test_cases = [
        ("你好", "Simple greeting (Chinese, fast-path)"),
        ("Hello!", "Simple greeting (English, fast-path)"),
        ("What is deep learning?", "Complex query (full workflow)"),
    ]
    
    print("\n⚡ Measuring Real LLM Latency:\n")
    
    for query, description in test_cases:
        print(f"📝 {description}")
        print(f"   Query: '{query}'")
        
        # Play acknowledgment (instant)
        t_start = time.time()
        await output.play_acknowledgment()
        
        # Stream response
        first_chunk_time = None
        chunk_count = 0
        
        print("   Response: ", end="", flush=True)
        
        try:
            async for chunk in agent.process_stream(query):
                chunk_count += 1
                
                if first_chunk_time is None:
                    first_chunk_time = (time.time() - t_start) * 1000
                    print(f"[{chunk}]", end="", flush=True)  # Highlight first chunk
                else:
                    print(chunk, end="", flush=True)
        
        except Exception as e:
            print(f"\n   ❌ Error: {e}")
            continue
        
        print()  # Newline
        
        total_time = (time.time() - t_start) * 1000
        
        # Report metrics
        if first_chunk_time:
            status = "✅" if first_chunk_time < 1000 else "⚠️"
            print(f"   {status} First token: {first_chunk_time:.0f}ms (target: <1000ms)")
            print(f"   📊 Total: {total_time:.0f}ms ({chunk_count} chunks)")
        
        print()
    
    print("=" * 60)
    print("✅ Real LLM streaming test complete!")
    print("\nℹ️  If first token > 1000ms, check:")
    print("   - Network latency to Doubao API")
    print("   - API tier/rate limits")
    print("   - Consider caching common responses")


if __name__ == "__main__":
    asyncio.run(test_real_llm_streaming())
