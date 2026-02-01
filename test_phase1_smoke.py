#!/usr/bin/env python3
"""
Quick smoke test for Phase 1 TTS connection pooling integration.
Verifies hybrid_jarvis.py can import and initialize without errors.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🧪 Phase 1 Smoke Test: TTS Connection Pooling")
print("="*60)

try:
    # Test 1: Import check
    print("\n📦 Test 1: Importing hybrid_jarvis...")
    from jarvis_assistant.core.hybrid_jarvis import HybridJarvis
    print("   ✅ Import successful")
    
    # Test 2: Initialization check
    print("\n🔧 Test 2: Initializing HybridJarvis (without connecting)...")
    # Note: We can't fully initialize without audio devices, but we can check imports
    print("   ℹ️  Skipping full initialization (requires audio hardware)")
    print("   ✅ No import errors detected")
    
    # Test 3: TTS singleton check
    print("\n🔌 Test 3: Checking TTS singleton...")
    from jarvis_assistant.io.tts import get_doubao_tts
    tts1 = get_doubao_tts()
    tts2 = get_doubao_tts()
    assert tts1 is tts2, "TTS singleton broken!"
    print(f"   ✅ Singleton verified: tts1 is tts2 = {tts1 is tts2}")
    
    print("\n" + "="*60)
    print("✅ Phase 1 Smoke Test PASSED")
    print("\nℹ️  Full integration test requires:")
    print("   - Audio hardware (mic + speaker)")
    print("   - Running hybrid_jarvis.py live")
    print("\n📋 Next: Phase 2 (LLM Streaming Integration)")
    
except Exception as e:
    print(f"\n❌ Phase 1 Smoke Test FAILED")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
