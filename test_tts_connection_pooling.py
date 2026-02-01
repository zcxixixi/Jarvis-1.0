#!/usr/bin/env python3
"""
Test TTS connection pooling optimization.
Verifies that reusing WebSocket connection reduces latency.
"""

import asyncio
import time
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

# Load environment from jarvis_assistant/.env
ENV_PATH = os.path.join(PROJECT_ROOT, "jarvis_assistant", ".env")
load_dotenv(ENV_PATH, override=True)


async def test_connection_pooling():
    """Test that singleton TTS instance reuses connection"""
    print("🧪 Testing TTS Connection Pooling")
    print("="*60)
    
    from jarvis_assistant.io.tts import get_doubao_tts
    
    # Get singleton instance
    tts1 = get_doubao_tts()
    
    # First request: expect connection establishment
    print("\n📍 Test 1: First request (cold start)")
    t0 = time.time()
    await tts1.speak("第一次连接测试")
    time1 = (time.time() - t0) * 1000
    print(f"   Latency: {time1:.0f}ms (includes connection)")
    
    # Second request: should reuse connection
    print("\n📍 Test 2: Second request (warm connection)")
    t0 = time.time()
    await tts1.speak("第二次连接测试")
    time2 = (time.time() - t0) * 1000
    print(f"   Latency: {time2:.0f}ms (reused connection)")
    
    # Third request: verify consistent reuse
    print("\n📍 Test 3: Third request (verify reuse)")
    t0 = time.time()
    await tts1.speak("第三次连接测试")
    time3 = (time.time() - t0) * 1000
    print(f"   Latency: {time3:.0f}ms (reused connection)")
    
    # Get same instance again (singleton pattern)
    tts2 = get_doubao_tts()
    assert tts1 is tts2, "Singleton pattern broken!"
    print(f"\n✅ Singleton verified: tts1 is tts2 = {tts1 is tts2}")
    
    # Fourth request: should still reuse
    print("\n📍 Test 4: Fourth request (same instance)")
    t0 = time.time()
    await tts2.speak("第四次连接测试")
    time4 = (time.time() - t0) * 1000
    print(f"   Latency: {time4:.0f}ms (reused connection)")
    
    # Close connection
    await tts1.close()
    
    # Verify reconnection after close
    print("\n📍 Test 5: After close (should reconnect)")
    t0 = time.time()
    await tts1.speak("关闭后重连测试")
    time5 = (time.time() - t0) * 1000
    print(f"   Latency: {time5:.0f}ms (reconnected)")
    
    await tts1.close()
    
    # Report results
    print("\n" + "="*60)
    print("📊 Results Summary:")
    print("-"*60)
    print(f"Test 1 (cold start):     {time1:.0f}ms")
    print(f"Test 2 (warm):           {time2:.0f}ms ({'✅' if time2 < time1 * 0.8 else '⚠️'})")
    print(f"Test 3 (warm):           {time3:.0f}ms ({'✅' if time3 < time1 * 0.8 else '⚠️'})")
    print(f"Test 4 (warm):           {time4:.0f}ms ({'✅' if time4 < time1 * 0.8 else '⚠️'})")
    print(f"Test 5 (reconnect):      {time5:.0f}ms")
    print("-"*60)
    
    # Calculate improvement
    avg_warm = (time2 + time3 + time4) / 3
    improvement = ((time1 - avg_warm) / time1) * 100
    
    print(f"\n🎯 Connection Pooling Improvement:")
    print(f"   Cold start: {time1:.0f}ms")
    print(f"   Warm (avg): {avg_warm:.0f}ms")
    print(f"   Savings: {improvement:.1f}% faster")
    
    if improvement > 20:
        print(f"\n✅ Connection pooling works! {improvement:.0f}% latency reduction")
    else:
        print(f"\n⚠️ Connection pooling may not be effective (only {improvement:.0f}% improvement)")
    
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_connection_pooling())
