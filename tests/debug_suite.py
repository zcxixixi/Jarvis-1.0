"""
Jarvis Debug Suite
Efficiently test components and VISUALIZE results.
"""
import sys
import time
import asyncio
import numpy as np
import matplotlib.pyplot as plt
from tools.netease_tools import NeteaseMusicTool
from aec_processor import SoftwareAEC

def test_aec_visualization():
    """Test 2: Verify AEC Cancellation Logic & Plot Result"""
    print("\n[Test 2] Testing AEC Cancellation & Generating Plot...")
    
    # Setup AEC
    sample_rate = 16000
    aec = SoftwareAEC(sample_rate=sample_rate)
    
    # 1. Generate Synthetic Data (5 seconds)
    duration = 5.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Reference: Complex signal (Speech-like spectrum)
    # Mix of several Sines + Noise to mimic speech/music
    ref_signal = (
        np.sin(2 * np.pi * 200 * t) * 3000 + 
        np.sin(2 * np.pi * 500 * t) * 2000 + 
        np.sin(2 * np.pi * 1000 * t) * 1000 +
        np.random.normal(0, 500, len(t))
    ).astype(np.int16)
    
    # Mic Input: Reference (Echo) + Near-end Speech (Target)
    # Simulate system delay: 200ms
    delay_samples = int(0.2 * sample_rate)
    echo_signal = np.roll(ref_signal, delay_samples)
    echo_signal[:delay_samples] = 0 # Leading zeros
    
    # Add a "Voice Command" in the middle (e.g. "Jarvis Stop")
    # This is what we want to KEEP
    voice_signal = np.zeros_like(t)
    voice_start = int(2.0 * sample_rate)
    voice_end = int(3.0 * sample_rate)
    voice_signal[voice_start:voice_end] = (np.sin(2 * np.pi * 600 * t[voice_start:voice_end]) * 8000).astype(np.int16)
    
    # Mic = Echo + Voice
    mic_signal = (echo_signal * 0.8 + voice_signal).astype(np.int16)
    
    # 2. Process with AEC
    ref_bytes = ref_signal.tobytes()
    mic_bytes = mic_signal.tobytes()
    
    # Feed Reference continuously 
    # (In real life, ref is fed slightly ahead of mic)
    chunk_size = 320 # 20ms
    processed_audio = bytearray()
    
    # Reset AEC just in case
    aec.reset()
    
    # Fill buffer a bit first (Simulate playback starting)
    aec.feed_reference(ref_bytes[:delay_samples])
    
    print("   -> Processing audio streams...")
    for i in range(0, len(mic_bytes), chunk_size*2):
        # Current Mic Chunk
        mic_chunk = mic_bytes[i:i+chunk_size*2]
        if len(mic_chunk) < chunk_size*2: break
        
        # Current Ref Chunk (Simulate reading next ref buffer)
        # We need to feed ref continuously as playhead moves
        ref_ptr = i + delay_samples
        if ref_ptr + chunk_size*2 < len(ref_bytes):
            ref_chunk = ref_bytes[ref_ptr:ref_ptr+chunk_size*2]
            aec.feed_reference(ref_chunk)
        else:
             aec.feed_reference(b'\x00' * (chunk_size*2))
             
        # Process
        out = aec.cancel_echo(mic_chunk)
        processed_audio.extend(out)
        
    out_signal = np.frombuffer(processed_audio, dtype=np.int16)
    
    # 3. Plot Results
    print("   -> Generating 'aec_result.png'...")
    plt.figure(figsize=(12, 8))
    
    # Plot 1: Composite Mic Input (What Jarvis heard raw)
    plt.subplot(3, 1, 1)
    plt.title("1. What Mic Hears (Echo + Voice Command)")
    # Show echo zone vs voice zone
    plt.plot(t[:len(out_signal)], mic_signal[:len(out_signal)], color='orange', label='Echo + Voice')
    plt.axvline(x=2.0, color='r', linestyle='--', alpha=0.5)
    plt.axvline(x=3.0, color='r', linestyle='--', alpha=0.5)
    plt.text(2.5, 10000, "Voice Command", ha='center', color='red')
    plt.ylabel("Amplitude")
    plt.grid(True, alpha=0.3)
    
    # Plot 2: Output (What Jarvis hears after AEC)
    plt.subplot(3, 1, 2)
    plt.title("2. What Jarvis Hears (After AEC)")
    plt.plot(t[:len(out_signal)], out_signal, color='green', label='Cleaned Audio')
    # Ideally, Echo (0-2s, 3-5s) should be reduced, Voice (2-3s) should remain
    plt.axvline(x=2.0, color='r', linestyle='--', alpha=0.5)
    plt.axvline(x=3.0, color='r', linestyle='--', alpha=0.5)
    plt.ylabel("Amplitude")
    plt.grid(True, alpha=0.3)
    
    # Plot 3: Energy Comparison
    plt.subplot(3, 1, 3)
    plt.title("3. Echo Reduction Analysis (dB)")
    # Calculate simple rolling energy
    window = 1000
    mic_energy = [np.mean(np.abs(mic_signal[i:i+window])) for i in range(0, len(out_signal), window)]
    out_energy = [np.mean(np.abs(out_signal[i:i+window])) for i in range(0, len(out_signal), window)]
    time_steps = np.linspace(0, duration, len(mic_energy))
    
    plt.plot(time_steps, mic_energy, color='orange', label='Raw Input Energy', alpha=0.7)
    plt.plot(time_steps, out_energy, color='green', label='AEC Output Energy', linewidth=2)
    plt.legend()
    plt.ylabel("Energy")
    plt.xlabel("Time (s)")
    
    plt.tight_layout()
    plt.savefig('aec_result.png')
    print("   -> ✅ Saved visualization to 'aec_result.png'")

async def main():
    test_aec_visualization()

if __name__ == "__main__":
    asyncio.run(main())
