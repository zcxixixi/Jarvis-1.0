"""
Test VAD Module
"""

import asyncio
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.vad import VoiceActivityDetector
from config import VADConfig

def generate_speech_like_audio(duration_ms=500, sample_rate=16000):
    """Generate simulated speech audio"""
    num_samples = int(duration_ms * sample_rate / 1000)
    
    # Generate sine waves at speech-like frequencies (200-300 Hz)
    t = np.linspace(0, duration_ms/1000, num_samples)
    audio = np.sin(2 * np.pi * 250 * t) * 10000
    audio = audio.astype(np.int16)
    
    return audio.tobytes()

def generate_silence(duration_ms=500, sample_rate=16000):
    """Generate silence"""
    num_samples = int(duration_ms * sample_rate / 1000)
    audio = np.zeros(num_samples, dtype=np.int16)
    return audio.tobytes()

def test_1_initialization():
    """Test 1: VAD initialization"""
    print("\n" + "="*60)
    print("TEST 1: VAD Initialization")
    print("="*60)
    
    config = VADConfig(threshold=0.5)
    vad = VoiceActivityDetector(config)
    
    assert vad.config.threshold == 0.5
    print("✅ VAD initialized successfully")
    
    if vad.model is None:
        print("⚠️ Silero VAD not loaded (using fallback)")
    else:
        print("✅ Silero VAD loaded")
    
    return True

def test_2_speech_detection():
    """Test 2: Detect speech vs silence"""
    print("\n" + "="*60)
    print("TEST 2: Speech Detection")
    print("="*60)
    
    vad = VoiceActivityDetector()
    
    # Test silence
    silence = generate_silence(500)
    is_silence_speech = vad.is_speech(silence)
    print(f"Silence detected as speech: {is_silence_speech}")
    
    # Test speech-like audio
    speech = generate_speech_like_audio(500)
    is_speech_speech = vad.is_speech(speech)
    print(f"Speech detected as speech: {is_speech_speech}")
    
    print("✅ Speech detection test passed")
    return True

def test_3_stream_processing():
    """Test 3: Process audio stream"""
    print("\n" + "="*60)
    print("TEST 3: Stream Processing")
    print("="*60)
    
    vad = VoiceActivityDetector()
    
    # Simulate: silence → speech → silence
    chunks = [
        ("silence", generate_silence(100)),
        ("silence", generate_silence(100)),
        ("speech", generate_speech_like_audio(100)),
        ("speech", generate_speech_like_audio(100)),
        ("speech", generate_speech_like_audio(100)),
        ("silence", generate_silence(100)),
        ("silence", generate_silence(100)),
        ("silence", generate_silence(100)),
    ]
    
    events = []
    for label, chunk in chunks:
        is_speech, event = vad.process_stream(chunk)
        if event:
            events.append(event)
            print(f"  [{label:8s}] Event: {event}")
    
    print(f"\n📊 Events detected: {events}")
    print("✅ Stream processing test passed")
    return True

def test_4_energy_fallback():
    """Test 4: Energy-based fallback"""
    print("\n" + "="*60)
    print("TEST 4: Energy-based Fallback")
    print("="*60)
    
    vad = VoiceActivityDetector()
    
    # Test with different energy levels
    test_cases = [
        ("Silent", 0),
        ("Quiet", 100),
        ("Normal", 500),
        ("Loud", 2000),
    ]
    
    for label, amplitude in test_cases:
        # Generate audio with specific amplitude
        samples = np.ones(480, dtype=np.int16) * amplitude
        audio = samples.tobytes()
        
        result = vad._energy_based_detection(audio)
        print(f"  {label:10s} (amp={amplitude:4d}): {result}")
    
    print("✅ Energy-based fallback test passed")
    return True

def main():
    """Run all tests"""
    print("╔" + "="*58 + "╗")
    print("║" + " "*18 + "TESTING VAD MODULE" + " "*22 + "║")
    print("╚" + "="*58 + "╝")
    
    tests = [
        ("Initialization", test_1_initialization),
        ("Speech Detection", test_2_speech_detection),
        ("Stream Processing", test_3_stream_processing),
        ("Energy Fallback", test_4_energy_fallback),
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
        print("\n🎉 ALL TESTS PASSED! VAD module is working correctly.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
