#!/usr/bin/env python3
"""
Test Phase 5: Self-Learning
Verifies that the agent learns from feedback.
"""

import asyncio
import sys
import shutil
from pathlib import Path

# Clean state
feedback_file = Path("~/.jarvis/feedback.json").expanduser()
if feedback_file.exists():
    feedback_file.unlink()

from agent_core import JarvisAgent

async def test_learning():
    print("🧠 Testing Self-Learning")
    print("=" * 60)
    
    agent = JarvisAgent()
    
    # 1. Perform a task (that we will complain about)
    print("\n1. Running task: '计算 1+1'")
    await agent.run("计算 1+1")
    
    # 2. Give negative feedback
    print("\n2. User complains: '不对'")
    response = await agent.run("不对")
    print(f"Agent: {response}")
    
    if "recorded" not in response.lower():
        print("❌ Feedback not recorded")
        return False
        
    # 3. Verify it was learned
    from feedback_manager import get_feedback_manager
    fb = get_feedback_manager()
    advice = fb.get_advice("计算 1+1")
    
    if len(advice) > 0:
        print(f"✅ Learned lesson: {advice[0]}")
        return True
    else:
        print("❌ Failed to recall lesson")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_learning())
    sys.exit(0 if success else 1)
