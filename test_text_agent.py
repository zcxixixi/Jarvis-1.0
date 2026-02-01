#!/usr/bin/env python3
"""
Text-to-Text Agent Test
Simple test of Agent text input → text output (no audio)

Tests:
1. Chinese input → Should get Chinese output
2. English input → Should get English output
"""

import asyncio
import sys
import os

sys.path.append(os.getcwd())

from jarvis_assistant.core.agent import get_agent

async def test_text_to_text():
    print("🤖 Text-to-Text Agent Test")
    print("=" * 60)
    
    agent = get_agent()
    print("✅ Agent ready\n")
    
    # Test cases: [language, query]
    test_cases = [
        ("Chinese", "你好"),
        ("English", "Hello"),
        ("Chinese", "今天天气怎么样"),
        ("English", "What's the weather like today"),
    ]
    
    for lang, query in test_cases:
        print(f"{'=' * 60}")
        print(f"Test: {query} (Expected: {lang} response)")
        print(f"{'=' * 60}")
        
        response = await agent.run(query)
        
        print(f"Input:  {query}")
        print(f"Output: {response}")
        print()
        
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(test_text_to_text())
