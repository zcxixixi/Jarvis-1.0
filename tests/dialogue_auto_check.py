#!/usr/bin/env python3
"""
Jarvis Automated Dialogue Tester
Tests continuous conversation, feature switching, and edge cases
without requiring voice input.
"""

import subprocess
import time
import sys
import os
import threading
import queue
import re

# Test scenarios
SCENARIOS = {
    "continuous_dialogue": {
        "name": "连续对话测试 (15秒窗口)",
        "commands": [
            ("Jarvis", 2, "唤醒"),
            ("现在几点", 3, "时间查询"),
            ("北京天气怎么样", 4, "天气查询"),
            ("谢谢", 2, "礼貌回复"),
        ],
    },
    "feature_switching": {
        "name": "功能快速切换",
        "commands": [
            ("Jarvis", 2, "唤醒"),
            ("计算 123 乘以 456", 3, "计算"),
            ("今天星期几", 3, "日期"),
            ("上海天气", 4, "天气"),
        ],
    },
    "edge_cases": {
        "name": "边界情况测试",
        "commands": [
            ("Jarvis", 2, "唤醒"),
            ("", 1, "空输入"),
            ("asdfghjkl 乱码", 3, "无效输入"),
            ("退下", 2, "休眠"),
        ],
    },
}


class JarvisTestRunner:
    def __init__(self, jarvis_script="../core/hybrid_jarvis.py"):
        self.jarvis_script = jarvis_script
        self.process = None
        self.output_queue = queue.Queue()
        self.reader_thread = None
        
    def _output_reader(self):
        """Background thread to read stdout"""
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.output_queue.put(line.strip())
        except Exception as e:
            self.output_queue.put(f"[READER ERROR] {e}")
    
    def start_jarvis(self):
        """Start Jarvis as a subprocess"""
        print("🚀 Starting Jarvis subprocess...")
        
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        # Add project root to PYTHONPATH
        base_dir = os.path.dirname(os.path.abspath(__file__)) # tests/
        project_root = os.path.dirname(os.path.dirname(base_dir)) # Jarvis/
        env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')
        
        self.process = subprocess.Popen(
            [sys.executable, self.jarvis_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            cwd=os.path.dirname(os.path.abspath(__file__)) or '.'
        )
        
        self.reader_thread = threading.Thread(target=self._output_reader, daemon=True)
        self.reader_thread.start()
        
        # Wait for initialization
        print("⏳ Waiting for Jarvis to initialize...")
        time.sleep(5)
        return True
    
    def send_command(self, text: str):
        """Send a command to Jarvis via stdin"""
        if self.process and self.process.stdin:
            self.process.stdin.write(text + '\n')
            self.process.stdin.flush()
            print(f"📤 Sent: {text}")
    
    def get_output(self, timeout=5, stop_pattern: str = None) -> list:
        """Collect output lines within timeout (optionally stop on pattern)"""
        lines = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                line = self.output_queue.get(timeout=0.1)
                lines.append(line)
                print(f"📥 {line}")
                if stop_pattern and re.search(stop_pattern, line):
                    break
            except queue.Empty:
                continue
        return lines
    
    def stop_jarvis(self):
        """Stop Jarvis subprocess"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("🛑 Jarvis stopped")
    
    def run_scenario(self, scenario_key: str) -> dict:
        """Run a single test scenario"""
        scenario = SCENARIOS[scenario_key]
        print(f"\n{'='*60}")
        print(f"🧪 {scenario['name']}")
        print(f"{'='*60}")
        
        results = []
        for cmd, wait_time, description in scenario['commands']:
            print(f"\n📝 Test: {description}")
            self.send_command(cmd)
            stop_pattern = None
            if cmd and cmd.strip() and cmd.strip().lower() not in ["jarvis", "贾维斯"]:
                stop_pattern = r"\[Turn Finished\]|Turn released"
            output = self.get_output(timeout=max(wait_time, 8), stop_pattern=stop_pattern)
            
            # Basic validation
            success = len(output) > 0 or cmd == ""
            results.append({
                "command": cmd,
                "description": description,
                "success": success,
                "output_lines": len(output),
            })
            
            status = "✅" if success else "⚠️"
            print(f"{status} {description}: {len(output)} lines output")
        
        return {
            "scenario": scenario['name'],
            "results": results,
            "passed": all(r['success'] for r in results),
        }


def run_quick_tool_tests():
    """Run quick tool tests without starting full Jarvis"""
    print("\n" + "="*60)
    print("🔧 Quick Tool Tests (No Jarvis subprocess needed)")
    print("="*60 + "\n")
    
    import asyncio
    # Add services directory to path so we can import tools
    base_dir = os.path.dirname(os.path.abspath(__file__)) # jarvis_assistant/tests
    jarvis_assistant_dir = os.path.dirname(base_dir) # jarvis_assistant
    project_root = os.path.dirname(jarvis_assistant_dir) # Jarvis (root)
    
    services_dir = os.path.join(jarvis_assistant_dir, "services")
    
    # Add paths
    sys.path.insert(0, services_dir) # for "from tools import ..."
    sys.path.insert(0, project_root) # for "from jarvis_assistant... import ..."
    
    async def test_tools():
        from tools import get_all_tools
        tools = {t.name: t for t in get_all_tools()}
        
        tests = [
            ("get_current_time", {}, "时间"),
            ("calculate", {"expression": "2+2"}, "计算"),
            ("get_weather", {"city": "北京"}, "天气"),
        ]
        
        results = []
        for name, args, desc in tests:
            try:
                result = await tools[name].execute(**args)
                print(f"✅ {desc}: {str(result)[:60]}...")
                results.append(True)
            except Exception as e:
                print(f"❌ {desc}: {e}")
                results.append(False)
        
        return all(results)
    
    return asyncio.run(test_tools())


def main():
    print("="*60)
    print("🤖 Jarvis Automated Dialogue Test Suite")
    print("="*60)
    
    # Phase 1: Quick tool tests
    tools_ok = run_quick_tool_tests()
    
    if not tools_ok:
        print("\n❌ Tool tests failed. Fix tools before running dialogue tests.")
        return 1
    
    # Phase 2: Dialogue tests (requires Jarvis subprocess)
    print("\n" + "="*60)
    print("🎭 Dialogue Tests")
    print("="*60)
    
    runner = JarvisTestRunner()
    
    try:
        if not runner.start_jarvis():
            print("❌ Failed to start Jarvis")
            return 1
        
        all_results = []
        for scenario_key in SCENARIOS:
            result = runner.run_scenario(scenario_key)
            all_results.append(result)
            time.sleep(2)  # Brief pause between scenarios
        
        # Summary
        print("\n" + "="*60)
        print("📊 Test Summary")
        print("="*60)
        
        for result in all_results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{status} - {result['scenario']}")
        
        total_passed = sum(1 for r in all_results if r['passed'])
        print(f"\n总计: {total_passed}/{len(all_results)} 场景通过")
        
        return 0 if total_passed == len(all_results) else 1
        
    finally:
        runner.stop_jarvis()


if __name__ == "__main__":
    sys.exit(main())
