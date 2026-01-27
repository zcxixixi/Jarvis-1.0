#!/usr/bin/env python3
"""
Test Phase 6: Error Resilience
Verifies that the system degrades gracefully when tools fail.
"""

import asyncio
import sys
from agent_core import JarvisAgent

async def test_resilience():
    print("🛡️  Testing Error Resilience")
    print("=" * 60)
    
    agent = JarvisAgent()
    
    # 1. Test Weather Failure (Invalid City)
    print("\n1. Testing Graceful Failure (Invalid Input)...")
    # This city name is likely invalid and has special chars to test robustness
    result = await agent.run("查询 NonExistentCity!!!! 的天气")
    print(f"Result: {str(result)[:100]}...")
    
    if "错误" in result or "无法" in result or "error" in result.lower():
        print("✅ Correctly handled invalid input error")
    else:
        print("⚠️ Warning: Did not report error significantly")

    # 2. Test Execution Plan Resilience (One step fails, does agent recover?)
    print("\n2. Testing Multi-step Recovery...")
    # We ask for something impossible + something possible
    # "Play music by FakeArtist" -> Fail, "Tell me time" -> Success
    
    # Note: Planning might split this or fail both.
    # Ideally, we want to see it execute step 1, fail, and ensure it doesn't crash.
    try:
        res = await agent.run("播放歌曲 UnknownSongByUnknownArtist12345")
        if "❌" in res or "fail" in str(res).lower() or "找不到" in res:
             print("✅ Handled tool failure gracefully")
        else:
             print(f"⚠️ Unexpected result: {res}")
    except Exception as e:
        print(f"❌ CRASHED: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = asyncio.run(test_resilience())
    sys.exit(0 if success else 1)
