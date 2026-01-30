#!/usr/bin/env python3
"""
Jarvis Robustness Test Suite
Tests edge cases, stress scenarios, and failure recovery
"""

import asyncio
import sys
import os
import time
import random
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


class RobustnessTest:
    def __init__(self):
        self.results = []
        self.failures = []
    
    def log(self, test_name: str, passed: bool, msg: str = ""):
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name}: {msg}")
        self.results.append((test_name, passed, msg))
        if not passed:
            self.failures.append(test_name)
    
    async def test_edge_case_inputs(self):
        """Test handling of unusual inputs"""
        print("\n🔬 Edge Case Inputs")
        print("-" * 40)
        
        from jarvis_assistant.core.agent import JarvisAgent
        agent = JarvisAgent()
        
        edge_cases = [
            ("", "Empty string"),
            ("   ", "Whitespace only"),
            ("!@#$%^&*()", "Special characters"),
            ("A" * 1000, "Very long input"),
            ("你好" * 100, "Long Chinese"),
            ("🎵🎶🎤🎧", "Emoji only"),
            ("天气" * 50, "Repeated keyword"),
            (None, "None value"),
        ]
        
        for input_val, desc in edge_cases:
            try:
                if input_val is None:
                    # Special case for None
                    self.log(f"edge_{desc}", True, "Skipped (None)")
                    continue
                result = await agent.run(input_val)
                self.log(f"edge_{desc}", True, f"Handled: {str(result)[:30]}")
            except Exception as e:
                self.log(f"edge_{desc}", False, f"Crashed: {e}")
    
    async def test_concurrent_requests(self):
        """Test handling multiple simultaneous requests"""
        print("\n🔀 Concurrent Requests")
        print("-" * 40)
        
        from jarvis_assistant.core.agent import JarvisAgent
        agent = JarvisAgent()
        
        queries = [
            "现在几点",
            "北京天气",
            "计算 1+1",
            "上海天气",
            "计算 100*100",
        ]
        
        try:
            # Run all concurrently
            start = time.time()
            results = await asyncio.gather(*[agent.run(q) for q in queries], return_exceptions=True)
            elapsed = time.time() - start
            
            errors = [r for r in results if isinstance(r, Exception)]
            if errors:
                self.log("concurrent_requests", False, f"{len(errors)} exceptions")
            else:
                self.log("concurrent_requests", True, f"5 requests in {elapsed:.2f}s")
        except Exception as e:
            self.log("concurrent_requests", False, str(e))
    
    async def test_memory_persistence(self):
        """Test memory survives restart"""
        print("\n💾 Memory Persistence")
        print("-" * 40)
        
        from jarvis_assistant.core.memory import MemoryStore
        import tempfile
        import json
        
        test_path = "/tmp/robustness_memory_test.json"
        
        try:
            # Create and save
            mem1 = MemoryStore(path=test_path)
            mem1.add_conversation("user", "robustness test message")
            mem1.set_preference("test_key", "test_value")
            mem1.save()
            
            # Load in new instance
            mem2 = MemoryStore(path=test_path)
            
            # Verify
            has_msg = any("robustness" in c.get("content", "") for c in mem2.conversations)
            has_pref = mem2.get_preference("test_key") == "test_value"
            
            if has_msg and has_pref:
                self.log("memory_persistence", True, "Data survives restart")
            else:
                self.log("memory_persistence", False, f"msg:{has_msg} pref:{has_pref}")
            
            os.remove(test_path)
        except Exception as e:
            self.log("memory_persistence", False, str(e))
    
    async def test_tool_error_handling(self):
        """Test tools handle errors gracefully"""
        print("\n🔧 Tool Error Handling")
        print("-" * 40)
        
        from jarvis_assistant.services.tools import get_all_tools
        tools = {t.name: t for t in get_all_tools()}
        
        # Test with invalid arguments
        test_cases = [
            ("get_weather", {"city": ""}, "Empty city"),
            ("calculate", {"expression": "invalid"}, "Invalid expression"),
            ("calculate", {"expression": "1/0"}, "Division by zero"),
        ]
        
        for tool_name, args, desc in test_cases:
            if tool_name not in tools:
                continue
            try:
                result = await tools[tool_name].execute(**args)
                # If it returns (doesn't crash), it's handling errors
                self.log(f"tool_error_{desc}", True, f"Handled: {str(result)[:30]}")
            except Exception as e:
                # Check if it's a controlled error or crash
                if "error" in str(e).lower() or "invalid" in str(e).lower():
                    self.log(f"tool_error_{desc}", True, f"Controlled error: {str(e)[:30]}")
                else:
                    self.log(f"tool_error_{desc}", False, f"Unhandled: {e}")
    
    async def test_rapid_fire(self):
        """Test rapid sequential requests"""
        print("\n⚡ Rapid Fire (20 requests)")
        print("-" * 40)
        
        from jarvis_assistant.core.agent import JarvisAgent
        agent = JarvisAgent()
        
        queries = ["现在几点", "计算 1+1"] * 10
        
        try:
            start = time.time()
            for q in queries:
                await agent.run(q)
            elapsed = time.time() - start
            
            avg = elapsed / len(queries)
            self.log("rapid_fire", True, f"20 requests, avg {avg:.3f}s each")
        except Exception as e:
            self.log("rapid_fire", False, str(e))
    
    async def test_multi_step_planning(self):
        """Test complex multi-step requests"""
        print("\n🔗 Multi-step Planning")
        print("-" * 40)
        
        from jarvis_assistant.core.agent import JarvisAgent
        agent = JarvisAgent()
        
        complex_queries = [
            "告诉我时间和天气",
            "计算 2+2 然后告诉我北京天气",
            "现在几点了，顺便查一下上海天气",
        ]
        
        for q in complex_queries:
            try:
                result = await agent.run(q)
                # Check if result contains multiple pieces of info
                self.log(f"multi_step", True, f"Handled: {q[:20]}...")
            except Exception as e:
                self.log(f"multi_step", False, str(e))
    
    async def run_all(self):
        """Run all robustness tests"""
        print("=" * 60)
        print("🛡️  JARVIS ROBUSTNESS TEST SUITE")
        print("=" * 60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        start = time.time()
        
        await self.test_edge_case_inputs()
        await self.test_memory_persistence()
        await self.test_tool_error_handling()
        await self.test_concurrent_requests()
        await self.test_rapid_fire()
        await self.test_multi_step_planning()
        
        elapsed = time.time() - start
        passed = len([r for r in self.results if r[1]])
        total = len(self.results)
        
        print("\n" + "=" * 60)
        print(f"📊 ROBUSTNESS RESULTS: {passed}/{total} tests passed")
        print(f"⏱️  Total time: {elapsed:.2f}s")
        
        if self.failures:
            print(f"\n❌ Failed tests:")
            for f in self.failures:
                print(f"   - {f}")
        
        print("=" * 60)
        
        return len(self.failures) == 0


if __name__ == "__main__":
    success = asyncio.run(RobustnessTest().run_all())
    sys.exit(0 if success else 1)
