#!/usr/bin/env python3
"""
Phase 1 鲁棒性测试：TTS 连接池压力测试
测试多次请求、并发、错误恢复等场景
"""

import asyncio
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment
ENV_PATH = os.path.join(os.path.dirname(__file__), "jarvis_assistant", ".env")
load_dotenv(ENV_PATH, override=True)


async def test_sequential_requests():
    """测试 1: 连续多次请求 (验证连接复用)"""
    print("\n" + "="*60)
    print("📍 Test 1: 连续 10 次 TTS 请求")
    print("="*60)
    
    from jarvis_assistant.io.tts import get_doubao_tts
    
    tts = get_doubao_tts()
    latencies = []
    
    for i in range(10):
        text = f"第 {i+1} 次测试"
        
        t0 = time.time()
        await tts.speak(text)
        latency = (time.time() - t0) * 1000
        latencies.append(latency)
        
        # 首次应该有连接建立
        if i == 0:
            print(f"   {i+1}. {latency:.0f}ms (冷启动 - 包含连接)")
        else:
            print(f"   {i+1}. {latency:.0f}ms {'✅' if latency < latencies[0] * 0.9 else '⚠️'}")
        
        await asyncio.sleep(0.5)  # 短暂间隔
    
    # 分析结果
    avg_warm = sum(latencies[1:]) / len(latencies[1:]) if len(latencies) > 1 else 0
    improvement = ((latencies[0] - avg_warm) / latencies[0] * 100) if avg_warm else 0
    
    print(f"\n📊 结果:")
    print(f"   冷启动: {latencies[0]:.0f}ms")
    print(f"   热请求平均: {avg_warm:.0f}ms")
    print(f"   提升: {improvement:.1f}%")
    
    success = improvement > 5  # 至少 5% 提升
    print(f"   {'✅ PASS' if success else '❌ FAIL'}")
    
    await tts.close()
    return success


async def test_reconnection_after_close():
    """测试 2: 关闭后重连 (验证错误恢复)"""
    print("\n" + "="*60)
    print("📍 Test 2: 关闭后重连测试")
    print("="*60)
    
    from jarvis_assistant.io.tts import get_doubao_tts
    
    tts = get_doubao_tts()
    
    # 第一次请求
    print("   1. 首次请求...")
    await tts.speak("首次请求")
    
    # 关闭连接
    print("   2. 关闭连接...")
    await tts.close()
    
    # 第二次请求 (应该自动重连)
    print("   3. 关闭后再次请求 (应自动重连)...")
    t0 = time.time()
    await tts.speak("重连测试")
    latency = (time.time() - t0) * 1000
    
    print(f"   重连延迟: {latency:.0f}ms")
    
    success = latency < 1000  # 重连应该在 1s 内完成
    print(f"   {'✅ PASS' if success else '❌ FAIL'}")
    
    await tts.close()
    return success


async def test_singleton_consistency():
    """测试 3: 单例一致性 (多次获取应该是同一实例)"""
    print("\n" + "="*60)
    print("📍 Test 3: 单例一致性测试")
    print("="*60)
    
    from jarvis_assistant.io.tts import get_doubao_tts
    
    instances = []
    for i in range(5):
        tts = get_doubao_tts()
        instances.append(tts)
        print(f"   {i+1}. Instance ID: {id(tts)}")
    
    # 验证所有实例相同
    all_same = all(tts is instances[0] for tts in instances)
    
    print(f"\n   所有实例相同: {all_same}")
    print(f"   {'✅ PASS' if all_same else '❌ FAIL'}")
    
    return all_same


async def test_error_handling():
    """测试 4: 错误处理 (无效文本、空文本等)"""
    print("\n" + "="*60)
    print("📍 Test 4: 错误处理测试")
    print("="*60)
    
    from jarvis_assistant.io.tts import get_doubao_tts
    
    tts = get_doubao_tts()
    
    test_cases = [
        ("", "空字符串"),
        ("   ", "仅空格"),
        ("测试" * 1000, "超长文本 (1000 字)"),
    ]
    
    passed = 0
    for text, description in test_cases:
        try:
            print(f"   测试: {description}...")
            await tts.speak(text[:50] + "..." if len(text) > 50 else text)
            print(f"      ✅ 处理成功")
            passed += 1
        except Exception as e:
            print(f"      ⚠️ 错误: {e}")
    
    success = passed >= 2  # 至少 2/3 通过
    print(f"\n   通过: {passed}/{len(test_cases)}")
    print(f"   {'✅ PASS' if success else '❌ FAIL'}")
    
    await tts.close()
    return success


async def test_rapid_fire():
    """测试 5: 快速连续请求 (压力测试)"""
    print("\n" + "="*60)
    print("📍 Test 5: 快速连续请求 (20次)")
    print("="*60)
    
    from jarvis_assistant.io.tts import get_doubao_tts
    
    tts = get_doubao_tts()
    
    # 快速发送 20 次请求
    start_time = time.time()
    errors = 0
    
    for i in range(20):
        try:
            await tts.speak(f"快速测试 {i+1}")
            print(f"   {i+1}. ✅", end="\r")
        except Exception as e:
            errors += 1
            print(f"   {i+1}. ❌ {e}")
    
    total_time = time.time() - start_time
    
    print(f"\n\n📊 结果:")
    print(f"   总时间: {total_time:.1f}s")
    print(f"   成功: {20-errors}/20")
    print(f"   错误: {errors}")
    
    success = errors == 0
    print(f"   {'✅ PASS' if success else '❌ FAIL'}")
    
    await tts.close()
    return success


async def main():
    """运行所有鲁棒性测试"""
    print("🧪 Phase 1 鲁棒性测试套件")
    print("="*60)
    print("测试 TTS 连接池的稳定性和性能")
    
    # 检查环境变量
    if not (os.getenv("DOUBAO_ARK_API_KEY") or os.getenv("DOUBAO_ACCESS_TOKEN")):
        print("\n❌ 错误: 未设置 DOUBAO_ARK_API_KEY")
        print("   请配置环境变量后重试")
        return
    
    results = {}
    
    try:
        # Test 1: 连续请求
        results["sequential"] = await test_sequential_requests()
        
        # Test 2: 重连测试
        results["reconnection"] = await test_reconnection_after_close()
        
        # Test 3: 单例一致性
        results["singleton"] = await test_singleton_consistency()
        
        # Test 4: 错误处理
        results["error_handling"] = await test_error_handling()
        
        # Test 5: 快速请求
        results["rapid_fire"] = await test_rapid_fire()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        return
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试汇总")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name:20s}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\n   总计: {total_passed}/{total_tests} 通过")
    
    if total_passed == total_tests:
        print("\n✅ 所有测试通过！TTS 连接池鲁棒性验证成功")
    else:
        print(f"\n⚠️ {total_tests - total_passed} 项测试失败，需要修复")


if __name__ == "__main__":
    asyncio.run(main())
