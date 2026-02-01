#!/usr/bin/env python3
"""
Test streaming agent with fast-path detection.
Validates <1s first token latency target.
"""

import asyncio
import time
from jarvis_assistant.agent import JarvisAgent
from jarvis_assistant.io.text import ConsoleInput, ConsoleOutput


async def test_streaming_agent():
    """Test agent streaming with latency measurement."""
    print("🧪 Testing Streaming Agent (Fast-path + Latency)")
    print("=" * 60)
    
    agent = JarvisAgent(session_id="streaming_test", enable_streaming=True)
    output = ConsoleOutput(prefix="Jarvis: ", enable_streaming_demo=True)
    
    # Test cases
    test_cases = [
        ("你好", "simple", "Greeting (Chinese)"),
        ("Hello", "simple", "Greeting (English)"),
        ("Thanks!", "simple", "Thank you"),
        ("What's the weather?", "complex", "Complex query (needs tool)"),
    ]
    
    print("\n📊 Testing Fast-path Detection:\n")
    
    for query, expected_type, description in test_cases:
        is_simple = agent._is_simple_query(query)
        detected = "simple" if is_simple else "complex"
        status = "✅" if detected == expected_type else "❌"
        
        print(f"{status} {description:30s} → {detected:8s} (expected: {expected_type})")
    
    # Test streaming latency
    print("\n" + "=" * 60)
    print("📊 Testing Streaming Latency:\n")
    
    test_queries = ["你好", "Hello, how are you?"]
    
    for query in test_queries:
        print(f"Query: '{query}'")
        
        # Play acknowledgment (instant feedback)
        await output.play_acknowledgment()
        
        # Stream response
        t0 = time.time()
        first_chunk_time = None
        
        chunk_count = 0
        async for chunk in agent.process_stream(query):
            chunk_count += 1
            if chunk_count == 1:
                first_chunk_time = (time.time() - t0) * 1000
            
            # Output chunk
            print(chunk, end="", flush=True)
        
        print()  # Newline
        
        total_time = (time.time() - t0) * 1000
        
        # Report metrics
        first_status = "✅" if first_chunk_time < 1000 else "❌"
        print(f"   First chunk: {first_chunk_time:.0f}ms {first_status}")
        print(f"   Total: {total_time:.0f}ms")
        print()
    
    print("=" * 60)
    print("✅ Streaming agent test complete!")


if __name__ == "__main__":
    asyncio.run(test_streaming_agent())
