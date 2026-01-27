#!/usr/bin/env python3
"""
Test Phase 4: Proactive Execution
Verifies that the scheduler triggers tasks correctly
"""

import asyncio
import sys
import time
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from jarvis_assistant.core.agent import JarvisAgent

async def test_scheduler():
    print("⏰ Testing Proactive Execution")
    print("=" * 60)
    
    agent = JarvisAgent()
    
    # 1. Schedule a reminder
    print("\n1. Setting reminder for 5 seconds...")
    # Using the tool name directly to be sure, or NL if parser is good enough
    # The new intent "提醒" maps to schedule_reminder
    
    # We can try Natural Language if the plan step works
    result = await agent.run("提醒我5秒后测试完成")
    print(f"Agent response: {result}")
    
    if "ID:" not in result:
        print("❌ Failed to schedule reminder")
        return False
        
    print("✅ Reminder scheduled. Waiting for trigger...")
    
    # 2. Wait for trigger
    # We need to capture stdout or hook into the callback to verify
    # For this test script, we'll just wait and see if it prints "⚡ Proactive Trigger"
    # We can override the handle_trigger to verify using a flag
    
    trigger_received = False
    
    original_handler = agent.handle_trigger
    
    async def mock_handler(prompt):
        nonlocal trigger_received
        print(f"  ⚡ CAPTURED TRIGGER: {prompt}")
        trigger_received = True
        # await original_handler(prompt) # Don't actually run to save time
        
    agent.handle_trigger = mock_handler
    # We need to update the callback in scheduler because it binds the method
    agent.scheduler.set_callback(mock_handler)
    
    # Wait up to 10 seconds
    for i in range(10):
        if trigger_received:
            break
        print(f"  Waiting... {i+1}s")
        await asyncio.sleep(1)
        
    if trigger_received:
        print("✅ PASS: Proactive trigger received!")
        return True
    else:
        print("❌ FAIL: No trigger received within 10s")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_scheduler())
    sys.exit(0 if success else 1)
