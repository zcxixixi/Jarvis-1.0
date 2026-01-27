#!/usr/bin/env python3
"""
Unified Test Runner (QA Automation)
Run all verifications in one go.
"""

import sys
import asyncio
import time
from importlib import import_module

TEST_SUITES = [
    ("system_health_check", "System Health & Authenticity"),
    ("test_scheduler", "Proactive Scheduler"),
    ("test_learning", "Self-Learning Loop"),
    ("test_resilience", "Error Resilience"),
]

def run_suite(module_name, description):
    print(f"\n🔵 Running Suite: {description} ({module_name}.py)")
    print("-" * 50)
    try:
        # Import dynamically
        mod = import_module(module_name)
        
        # Check if it has a main entry point we can call, or run it via subprocess
        # Since these scripts have `if __name__ == "__main__":`, using subprocess is safer/cleaner
        import subprocess
        result = subprocess.run([sys.executable, f"{module_name}.py"], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("⚠️ STDERR:")
            print(result.stderr)
            
        if result.returncode == 0:
            print(f"✅ PASS: {description}")
            return True
        else:
            print(f"❌ FAIL: {description} (Exit Code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Could not run {module_name}: {e}")
        return False

def main():
    print("🚀 STARTING AUTOMATED REGRESSION SUITE")
    print("========================================")
    start_time = time.time()
    
    results = []
    for module, desc in TEST_SUITES:
        success = run_suite(module, desc)
        results.append((desc, success))
        
    print("\n========================================")
    print("📊 TEST SUMMARY")
    print("========================================")
    all_pass = True
    for desc, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {desc}")
        if not success: all_pass = False
        
    duration = time.time() - start_time
    print(f"\n⏱️  Total Time: {duration:.2f}s")
    
    if all_pass:
        print("\n🎉 QUALITY GATE PASSED: READY FOR DEPLOY")
        sys.exit(0)
    else:
        print("\n🚫 QUALITY GATE FAILED: DO NOT DEPLOY")
        sys.exit(1)

if __name__ == "__main__":
    main()
