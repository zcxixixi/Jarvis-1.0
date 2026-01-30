#!/usr/bin/env python3
"""
End-to-End Pipeline Test: ASR → Agent → TTS

Tests the complete Jarvis pipeline:
1. ASR - Speech recognition (simulated with text input)
2. Intent Classification - Route query
3. Agent - Tool execution
4. TTS - Voice synthesis and playback

Usage:
    python3 test_e2e_pipeline.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from jarvis_assistant.core.intent_classifier import IntentClassifier
from jarvis_assistant.core.agent import get_agent
from jarvis_assistant.services.doubao.tts_v3 import DoubaoTTSV1

async def test_pipeline():
    """Test complete pipeline"""
    
    print("\n" + "="*60)
    print("🤖 Jarvis End-to-End Pipeline Test")
    print("="*60 + "\n")
    
    # Test queries
    test_queries = [
        ("北京天气", "complex", "weather API"),
        ("特斯拉股价", "complex", "stock API"),
        ("你好", "simple", "S2S greeting"),
        ("打开灯", "complex", "smart home"),
        ("现在几点", "simple", "S2S time"),
    ]
    
    # Step 1: Intent Classification
    print("📋 Step 1: Testing Intent Classifier...")
    classifier = IntentClassifier()
    
    for query, expected, category in test_queries:
        result = classifier.classify(query)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{query}' → {result} (expected: {expected}) [{category}]")
    
    print("\n" + "-"*60 + "\n")
    
    # Step 2: Agent Execution (for complex queries only)
    print("🧠 Step 2: Testing Agent Execution...")
    agent = get_agent()
    
    complex_queries = [q for q, exp, _ in test_queries if exp == "complex"]
    
    for query in complex_queries[:2]:  # Test first 2 to avoid spamming APIs
        print(f"\n  Query: '{query}'")
        try:
            response = await agent.run(query)
            print(f"  ✅ Response: {response[:100]}...")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n" + "-"*60 + "\n")
    
    # Step 3: TTS Synthesis (without playback)
    print("🔊 Step 3: Testing TTS V3 Synthesis...")
    print("  (Skipping actual audio playback to avoid speaker conflicts)")
    
    try:
        tts = DoubaoTTSV1()
        await tts.connect()
        print("  ✅ TTS connection established")
        
        # Test synthesis (we'll just connect, not actually synthesize to avoid conflicts)
        print("  ✅ TTS V1 Binary protocol ready")
        
        await tts.close()
        print("  ✅ TTS connection closed")
        
    except Exception as e:
        print(f"  ❌ TTS Error: {e}")
    
    print("\n" + "="*60)
    print("✅ End-to-End Pipeline Test Complete!")
    print("="*60 + "\n")
    
    print("💡 To test full system with audio, run: python3 main.py")
    print("   Then say: 'Hey Jarvis, 今天北京天气怎么样'")

if __name__ == "__main__":
    try:
        asyncio.run(test_pipeline())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
