#!/usr/bin/env python3
"""
User Experience Test Suite
Tests focused on user comfort and satisfaction
"""

import asyncio
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


async def test_startup_speed():
    """Test: Agent starts quickly (user doesn't wait)"""
    print("\n🚀 Test 1: Startup Speed")
    print("-" * 40)
    
    start = time.time()
    from jarvis_assistant.core.agent import JarvisAgent
    agent = JarvisAgent()
    elapsed = time.time() - start
    
    # Pass criteria: < 3 seconds
    if elapsed < 3.0:
        print(f"✅ PASS: Agent loaded in {elapsed:.2f}s (user comfortable)")
        return True
    else:
        print(f"❌ FAIL: Took {elapsed:.2f}s (user waiting too long)")
        return False


async def test_response_time():
    """Test: Quick responses (user not frustrated)"""
    print("\n⚡ Test 2: Response Time")
    print("-" * 40)
    
    from jarvis_assistant.core.agent import JarvisAgent
    agent = JarvisAgent()
    
    queries = ["现在几点", "计算 2+2", "北京天气"]
    times = []
    
    for q in queries:
        start = time.time()
        result = await agent.run(q)
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  {q}: {elapsed:.2f}s")
    
    avg = sum(times) / len(times)
    
    # Pass criteria: avg < 2.0 seconds
    if avg < 2.0:
        print(f"✅ PASS: Avg {avg:.2f}s (feels instant to user)")
        return True
    else:
        print(f"❌ FAIL: Avg {avg:.2f}s (user notices delay)")
        return False


async def test_error_friendliness():
    """Test: Errors don't scare users"""
    print("\n😊 Test 3: Error Messages")
    print("-" * 40)
    
    from jarvis_assistant.core.agent import JarvisAgent
    agent = JarvisAgent()
    
    # Trigger errors
    bad_inputs = ["", "!@#$", "计算 xxx"]
    
    friendly = True
    for inp in bad_inputs:
        try:
            result = await agent.run(inp)
            # Check if error message is friendly
            if "error" in str(result).lower() or "错误" in str(result):
                # Has error indicator - check if scary
                if "crash" in str(result).lower() or "failed" in str(result).lower():
                    print(f"  ❌ '{inp}': Scary error message")
                    friendly = False
                else:
                    print(f"  ✅ '{inp}': Friendly error")
            else:
                print(f"  ✅ '{inp}': Handled gracefully")
        except Exception as e:
            print(f"  ❌ '{inp}': Crashed with {e}")
            friendly = False
    
    if friendly:
        print("✅ PASS: All errors handled gracefully")
        return True
    else:
        print("❌ FAIL: Some errors are scary")
        return False


async def test_plugin_transparency():
    """Test: User doesn't see plugin loading"""
    print("\n🔌 Test 4: Plugin Loading Transparency")
    print("-" * 40)
    
    start = time.time()
    
    # Capture output
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        from jarvis_assistant.core.agent import JarvisAgent
        agent = JarvisAgent()
    
    output = f.getvalue()
    elapsed = time.time() - start
    
    # Check if user sees too much plugin detail
    junk_words = ["discovered", "loading", "module", "import"]
    junk_count = sum(1 for word in junk_words if word in output.lower())
    
    if junk_count > 3:
        print(f"❌ FAIL: Too much technical output ({junk_count} junk words)")
        print(f"  User sees: {output[:200]}...")
        return False
    elif elapsed < 3.0:
        print(f"✅ PASS: Clean startup, {elapsed:.2f}s")
        return True
    else:
        print(f"⚠️  PARTIAL: Clean but slow ({elapsed:.2f}s)")
        return True


async def test_memory_persistence():
    """Test: User's history is remembered"""
    print("\n💭 Test 5: Memory Continuity")
    print("-" * 40)
    
    from jarvis_assistant.core.agent import JarvisAgent
    agent = JarvisAgent()
    
    # Ask something
    await agent.run("我叫测试用户")
    
    # Check if remembered
    history = agent.get_history(limit=5)
    
    if "测试用户" in history:
        print("✅ PASS: User's information remembered")
        return True
    else:
        print("❌ FAIL: User has to repeat themselves")
        return False


async def main():
    print("=" * 60)
    print("👤 USER EXPERIENCE TEST SUITE")
    print("=" * 60)
    print("Testing: Does it make users comfortable?")
    
    results = []
    
    results.append(await test_startup_speed())
    results.append(await test_response_time())
    results.append(await test_error_friendliness())
    results.append(await test_plugin_transparency())
    results.append(await test_memory_persistence())
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    print(f"📊 USER EXPERIENCE: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ READY: Users will be comfortable")
    elif passed >= total * 0.8:
        print("⚠️  NEEDS WORK: Some issues found")
    else:
        print("❌ NOT READY: Users will be frustrated")
    
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
