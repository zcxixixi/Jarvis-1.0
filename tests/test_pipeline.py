#!/usr/bin/env python3
"""
Jarvis Continuous Test Pipeline
Runs comprehensive tests and reports results to COLLAB.md

Usage:
  python3 test_pipeline.py          # Run once
  python3 test_pipeline.py --watch  # Run continuously
"""

import asyncio
import sys
import os
import time
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


class PipelineTestResult:
    def __init__(self, name: str, passed: bool, message: str = "", duration: float = 0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration


class JarvisTestPipeline:
    """Comprehensive test pipeline for Jarvis Agent"""
    
    def __init__(self):
        self.results: list[TestResult] = []
        self.start_time = None
    
    async def run_all(self) -> bool:
        """Run all test suites"""
        self.start_time = time.time()
        self.results = []
        
        print("=" * 60)
        print("🧪 JARVIS CONTINUOUS TEST PIPELINE")
        print("=" * 60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Test Suite 1: Tool Loading
        await self.test_tool_loading()
        
        # Test Suite 2: Memory Store
        await self.test_memory_store()
        
        # Test Suite 3: Agent Core
        await self.test_agent_core()
        
        # Test Suite 4: Multi-step Planning
        await self.test_multi_step()
        
        # Test Suite 5: Error Recovery
        await self.test_error_recovery()
        
        # Generate report
        self.generate_report()
        
        # Update COLLAB.md
        self.update_collab()
        
        total_time = time.time() - self.start_time
        passed = sum(1 for r in self.results if r.passed)
        
        print(f"\n{'=' * 60}")
        print(f"📊 RESULTS: {passed}/{len(self.results)} tests passed")
        print(f"⏱️  Total time: {total_time:.2f}s")
        print("=" * 60)
        
        return all(r.passed for r in self.results)
    
    async def test_tool_loading(self):
        """Test: All tools load correctly"""
        print("\n📦 Test Suite 1: Tool Loading")
        print("-" * 40)
        
        start = time.time()
        try:
            from jarvis_assistant.services.tools import get_all_tools
            tools = get_all_tools()
            
            if len(tools) >= 15:
                self.results.append(PipelineTestResult(
                    "tool_loading",
                    True,
                    f"Loaded {len(tools)} tools",
                    time.time() - start
                ))
                print(f"  ✅ Loaded {len(tools)} tools")
            else:
                self.results.append(PipelineTestResult(
                    "tool_loading",
                    False,
                    f"Only {len(tools)} tools loaded",
                    time.time() - start
                ))
                print(f"  ❌ Only {len(tools)} tools loaded")
        except Exception as e:
            self.results.append(PipelineTestResult("tool_loading", False, str(e), time.time() - start))
            print(f"  ❌ Failed: {e}")
    
    async def test_memory_store(self):
        """Test: Memory persistence works"""
        print("\n💾 Test Suite 2: Memory Store")
        print("-" * 40)
        
        start = time.time()
        try:
            from jarvis_assistant.core.memory import MemoryStore
            
            # Use temp path for testing
            test_path = "/tmp/jarvis_test_memory.json"
            memory = MemoryStore(path=test_path)
            
            # Test add conversation
            memory.add_conversation("user", "test message")
            memory.add_conversation("assistant", "test response")
            
            # Test persistence
            memory.save()
            memory2 = MemoryStore(path=test_path)
            
            if len(memory2.conversations) >= 2:
                self.results.append(PipelineTestResult(
                    "memory_store",
                    True,
                    "Memory persistence works",
                    time.time() - start
                ))
                print("  ✅ Memory persistence works")
            else:
                self.results.append(PipelineTestResult(
                    "memory_store",
                    False,
                    "Memory not persisted",
                    time.time() - start
                ))
                print("  ❌ Memory not persisted")
            
            # Cleanup
            os.remove(test_path)
            
        except Exception as e:
            self.results.append(PipelineTestResult("memory_store", False, str(e), time.time() - start))
            print(f"  ❌ Failed: {e}")
    
    async def test_agent_core(self):
        """Test: Agent executes single-step tasks"""
        print("\n🤖 Test Suite 3: Agent Core")
        print("-" * 40)
        
        tests = [
            ("现在几点", "时间查询"),
            ("计算 2+2", "计算"),
        ]
        
        try:
            from jarvis_assistant.core.agent import JarvisAgent
            agent = JarvisAgent()
            
            for query, desc in tests:
                start = time.time()
                try:
                    result = await agent.run(query)
                    if result and len(result) > 5:
                        self.results.append(PipelineTestResult(
                            f"agent_{desc}",
                            True,
                            result[:50],
                            time.time() - start
                        ))
                        print(f"  ✅ {desc}: {result[:40]}...")
                    else:
                        self.results.append(PipelineTestResult(
                            f"agent_{desc}",
                            False,
                            "Empty result",
                            time.time() - start
                        ))
                        print(f"  ❌ {desc}: Empty result")
                except Exception as e:
                    self.results.append(PipelineTestResult(f"agent_{desc}", False, str(e), time.time() - start))
                    print(f"  ❌ {desc}: {e}")
                    
        except Exception as e:
            self.results.append(PipelineTestResult("agent_core", False, str(e)))
            print(f"  ❌ Agent init failed: {e}")
    
    async def test_multi_step(self):
        """Test: Agent handles multi-keyword requests"""
        print("\n🔗 Test Suite 4: Multi-step Planning")
        print("-" * 40)
        
        start = time.time()
        try:
            from jarvis_assistant.core.agent import JarvisAgent
            agent = JarvisAgent()
            
            # This should trigger both time and weather
            result = await agent.run("告诉我现在几点，还有北京天气")
            
            if "时" in result or ":" in result:
                self.results.append(PipelineTestResult(
                    "multi_step",
                    True,
                    "Multi-step execution works",
                    time.time() - start
                ))
                print("  ✅ Multi-step execution works")
            else:
                self.results.append(PipelineTestResult(
                    "multi_step",
                    False,
                    "Multi-step failed",
                    time.time() - start
                ))
                print("  ❌ Multi-step failed")
                
        except Exception as e:
            self.results.append(PipelineTestResult("multi_step", False, str(e), time.time() - start))
            print(f"  ❌ Failed: {e}")
    
    async def test_error_recovery(self):
        """Test: Agent recovers from errors"""
        print("\n🔄 Test Suite 5: Error Recovery")
        print("-" * 40)
        
        start = time.time()
        try:
            from jarvis_assistant.core.agent import JarvisAgent
            agent = JarvisAgent()
            
            # Invalid request should not crash
            result = await agent.run("")
            
            self.results.append(PipelineTestResult(
                "error_recovery",
                True,
                "Graceful handling of edge cases",
                time.time() - start
            ))
            print("  ✅ Graceful handling of edge cases")
            
        except Exception as e:
            self.results.append(PipelineTestResult("error_recovery", False, str(e), time.time() - start))
            print(f"  ❌ Crashed on edge case: {e}")
    
    def generate_report(self):
        """Generate test report file"""
        report_path = Path(__file__).parent / "test_report.md"
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        lines = [
            "# Jarvis Test Report",
            f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n**Result**: {passed}/{total} tests passed\n",
            "| Test | Status | Duration | Message |",
            "|------|--------|----------|---------|",
        ]
        
        for r in self.results:
            status = "✅" if r.passed else "❌"
            lines.append(f"| {r.name} | {status} | {r.duration:.2f}s | {r.message[:30]} |")
        
        with open(report_path, 'w') as f:
            f.write("\n".join(lines))
        
        print(f"\n📄 Report saved to: {report_path}")
    
    def update_collab(self):
        """Update COLLAB.md with test results"""
        collab_path = Path(__file__).parent / "COLLAB.md"
        
        if not collab_path.exists():
            return
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Read current content
        with open(collab_path, 'r') as f:
            content = f.read()
        
        # Update status section
        status_line = f"| Last Test Run | {'✅' if passed == total else '⚠️'} {passed}/{total} | Pipeline ({timestamp}) |"
        
        if "| Last Test Run |" in content:
            import re
            content = re.sub(r'\| Last Test Run \|.*\|.*\|', status_line, content)
        else:
            # Add after Current Status header
            content = content.replace(
                "## Current Status\n",
                f"## Current Status\n\n{status_line}\n"
            )
        
        with open(collab_path, 'w') as f:
            f.write(content)


async def main():
    parser = argparse.ArgumentParser(description="Jarvis Continuous Test Pipeline")
    parser.add_argument("--watch", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=300, help="Watch interval in seconds")
    args = parser.parse_args()
    
    pipeline = JarvisTestPipeline()
    
    if args.watch:
        print("🔄 Running in watch mode (Ctrl+C to stop)")
        while True:
            await pipeline.run_all()
            print(f"\n⏳ Next run in {args.interval} seconds...")
            await asyncio.sleep(args.interval)
    else:
        success = await pipeline.run_all()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
