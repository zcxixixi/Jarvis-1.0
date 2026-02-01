#!/usr/bin/env python3
"""
Quick UX Improvement: Add input validation and timeout
Based on test findings from comprehensive UX testing
"""

import asyncio
import sys
sys.path.append('.')

from jarvis_assistant.core.agent import get_agent

async def test_improvements():
    """Test the UX improvements"""
    agent = get_agent()
    
    print("🧪 Testing UX Improvements\n")
    
    # Test 1: Empty input (should fail gracefully)
    print("Test 1: Empty input")
    try:
        response = await agent.run("")
        print(f"✅ Response: {response}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # Test 2: Whitespace only
    print("Test 2: Whitespace only")
    try:
        response = await agent.run("   ")
        print(f"✅ Response: {response}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # Test 3: Valid input (baseline)
    print("Test 3: Valid input (你好)")
    try:
        response = await agent.run("你好")
        print(f"✅ Response: {response[:100]}...\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(test_improvements())
