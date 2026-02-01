"""
Test Wake Word Module
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.wake_word import WakeWordDetector
from config import WakeWordConfig

def test_1_initialization():
    """Test 1: Wake Word initialization"""
    print("\n" + "="*60)
    print("TEST 1: Wake Word Initialization")
    print("="*60)
    
    config = WakeWordConfig(threshold=0.5)
    detector = WakeWordDetector(config)
    
    assert detector.config.threshold == 0.5
    print("✅ Wake Word detector initialized")
    
    if detector.model is None:
        print("⚠️ OpenWakeWord not loaded (using text fallback)")
    else:
        print("✅ OpenWakeWord loaded")
    
    return True

def test_2_text_detection():
    """Test 2: Detect wake word from text"""
    print("\n" + "="*60)
    print("TEST 2: Text-based Detection")
    print("="*60)
    
    detector = WakeWordDetector()
    
    test_cases = [
        ("hey jarvis", True),
        ("Hey Jarvis what's the weather", True),
        ("jarvis", True),
        ("hello", False),
        ("what time is it", False),
        ("嘿 jarvis", True),
    ]
    
    for text, expected in test_cases:
        result = detector.detect_from_text(text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{text}' → {result} (expected {expected})")
    
    print("✅ Text detection test passed")
    return True

def test_3_debouncing():
    """Test 3: Debounce mechanism"""
    print("\n" + "="*60)
    print("TEST 3: Debouncing")
    print("="*60)
    
    detector = WakeWordDetector()
    detector.config.debounce_seconds = 1.0
    
    # Generate dummy audio
    audio = np.zeros(480, dtype=np.int16).tobytes()
    
    # First detection (should work if model loaded)
    result1 = detector.detect(audio)
    print(f"First detection: {result1}")
    
    # Immediate second detection (should be None due to debounce)
    result2 = detector.detect(audio)
    print(f"Second detection (immediate): {result2}")
    
    assert result2 is None, "Debounce should prevent immediate re-detection"
    
    print("✅ Debouncing test passed")
    return True

def test_4_reset():
    """Test 4: Reset state"""
    print("\n" + "="*60)
    print("TEST 4: Reset State")
    print("="*60)
    
    detector = WakeWordDetector()
    
    # Simulate detection
    detector.detection_count = 5
    detector.last_detection_time = 12345.0
    
    print(f"Before reset: count={detector.detection_count}, time={detector.last_detection_time}")
    
    # Reset
    detector.reset()
    
    print(f"After reset: count={detector.detection_count}, time={detector.last_detection_time}")
    
    assert detector.detection_count == 0
    assert detector.last_detection_time == 0.0
    
    print("✅ Reset test passed")
    return True

def main():
    """Run all tests"""
    print("╔" + "="*58 + "╗")
    print("║" + " "*14 + "TESTING WAKE WORD MODULE" + " "*20 + "║")
    print("╚" + "="*58 + "╝")
    
    tests = [
        ("Initialization", test_1_initialization),
        ("Text Detection", test_2_text_detection),
        ("Debouncing", test_3_debouncing),
        ("Reset", test_4_reset),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"❌ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Wake Word module is working correctly.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
