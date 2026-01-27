#!/usr/bin/env python3
"""
Audio Latency Profiler for Jarvis
Measures audio pipeline performance
"""

import time
import pyaudio
import numpy as np
from collections import deque


def test_audio_latency():
    """Test audio output latency"""
    print("🎵 Audio Latency Profiler")
    print("=" * 60)
    
    p = pyaudio.PyAudio()
    
    # Use pulse device (same as Jarvis)
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=24000,
        output=True,
        output_device_index=2  # pulse
    )
    
    # Generate test tone
    duration = 0.1  # 100ms chunks
    sample_rate = 24000
    frequency = 440  # A4 note
    
    samples = int(duration * sample_rate)
    t = np.linspace(0, duration, samples)
    tone = (np.sin(2 * np.pi * frequency * t) * 32767 * 0.1).astype(np.int16)  # Quieter volume
    
    latencies = []
    
    print("\nTesting 50 audio chunks...")
    for i in range(50):
        start = time.time()
        stream.write(tone.tobytes())
        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)
        
        if i % 10 == 0:
            print(f"  Chunk {i}: {latency_ms:.2f}ms")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Statistics
    avg = np.mean(latencies)
    std = np.std(latencies)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    max_lat = max(latencies)
    
    print("\n" + "=" * 60)
    print("📊 Results:")
    print(f"  Average:   {avg:.2f}ms")
    print(f"  Std Dev:   {std:.2f}ms")
    print(f"  95th %%:    {p95:.2f}ms")
    print(f"  99th %%:    {p99:.2f}ms")
    print(f"  Max:       {max_lat:.2f}ms")
    print("=" * 60)
    
    # Diagnosis
    if avg < 10:
        print("✅ Excellent latency")
    elif avg < 50:
        print("✅ Good latency")
    elif avg < 100:
        print("⚠️  Moderate latency - may cause minor stuttering")
    else:
        print("❌ High latency - likely packet loss")
    
    # Assertions for pytest
    # Relaxed threshold for Mac hardware buffer (typically ~100ms)
    assert avg < 120, f"Average latency too high: {avg:.2f}ms"
    assert max_lat < 500, f"Max latency spike too high: {max_lat:.2f}ms"


if __name__ == "__main__":
    test_audio_latency()
