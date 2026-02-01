#!/usr/bin/env python3
"""
Comprehensive Agent UX Test Suite
Tests all agent capabilities and records input/output for analysis
"""

import asyncio
import sys
import os
import json
from datetime import datetime

sys.path.append(os.getcwd())

from jarvis_assistant.core.agent import get_agent

class TestRecorder:
    def __init__(self):
        self.results = []
        
    def record(self, category, input_text, output_text, metadata=None):
        """Record test result"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "input": input_text,
            "output": output_text,
            "metadata": metadata or {}
        }
        self.results.append(result)
        return result
    
    def save_to_file(self, filename="test_results.json"):
        """Save all results to JSON file"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Saved {len(self.results)} test results to {filename}")

async def run_comprehensive_tests():
    print("🧪 Comprehensive Agent UX Test Suite")
    print("=" * 70)
    
    agent = get_agent()
    recorder = TestRecorder()
    
    # Test Categories
    test_suites = {
        "Greetings": [
            "你好",
            "Hello",
            "嗨",
            "Hey there",
        ],
        "Weather Queries": [
            "今天天气怎么样",
            "What's the weather like today",
            "北京天气",
            "Weather in Beijing",
        ],
        "Knowledge Questions": [
            "什么是深度学习",
            "What is deep learning",
            "解释一下强化学习",
            "Explain reinforcement learning",
        ],
        "Memory Recall": [
            "我在研究什么",
            "What am I working on",
            "我的项目是什么",
            "Tell me about my research",
        ],
        "Music Control": [
            "播放音乐",
            "Play some music",
            "停止音乐",
            "Stop the music",
        ],
        "Edge Cases": [
            "",  # Empty input
            "asdfghjkl",  # Gibberish
            "你好hello混合",  # Mixed language
            "帮我做饭",  # Impossible request
        ],
    }
    
    for category, queries in test_suites.items():
        print(f"\n{'=' * 70}")
        print(f"📋 Testing: {category}")
        print(f"{'=' * 70}\n")
        
        for i, query in enumerate(queries, 1):
            try:
                print(f"[{i}/{len(queries)}] Input: '{query}'")
                
                # Run agent
                start_time = datetime.now()
                response = await agent.run(query)
                end_time = datetime.now()
                latency_ms = (end_time - start_time).total_seconds() * 1000
                
                # Detect language
                is_chinese_input = any('\u4e00' <= c <= '\u9fff' for c in query)
                is_chinese_output = any('\u4e00' <= c <= '\u9fff' for c in response)
                
                # Record result
                recorder.record(
                    category=category,
                    input_text=query,
                    output_text=response,
                    metadata={
                        "latency_ms": latency_ms,
                        "input_lang": "Chinese" if is_chinese_input else "English",
                        "output_lang": "Chinese" if is_chinese_output else "English",
                        "lang_match": is_chinese_input == is_chinese_output,
                    }
                )
                
                # Display
                print(f"   Output: {response[:80]}{'...' if len(response) > 80 else ''}")
                print(f"   Latency: {latency_ms:.0f}ms")
                print(f"   Lang: {recorder.results[-1]['metadata']['input_lang']} → {recorder.results[-1]['metadata']['output_lang']}")
                
                # Check language mismatch
                if recorder.results[-1]['metadata']['lang_match']:
                    print(f"   ✅ Language matched")
                else:
                    print(f"   ⚠️  Language mismatch!")
                
                print()
                
                await asyncio.sleep(0.5)  # Avoid rate limiting
                
            except Exception as e:
                print(f"   ❌ Error: {e}\n")
                recorder.record(
                    category=category,
                    input_text=query,
                    output_text=f"ERROR: {str(e)}",
                    metadata={"error": True}
                )
    
    # Save results
    recorder.save_to_file("test_results.json")
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    
    total = len(recorder.results)
    errors = sum(1 for r in recorder.results if r.get("metadata", {}).get("error"))
    lang_mismatches = sum(1 for r in recorder.results 
                          if not r.get("metadata", {}).get("lang_match", True) 
                          and not r.get("metadata", {}).get("error"))
    
    avg_latency = sum(r.get("metadata", {}).get("latency_ms", 0) 
                      for r in recorder.results if not r.get("metadata", {}).get("error")) / (total - errors) if total > errors else 0
    
    print(f"Total tests: {total}")
    print(f"Errors: {errors}")
    print(f"Language mismatches: {lang_mismatches}")
    print(f"Average latency: {avg_latency:.0f}ms")
    print(f"\nDetailed results saved to: test_results.json")

if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())
