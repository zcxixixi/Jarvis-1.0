"""
Synthetic AEC Verification (No Mic Needed)
-----------------------------------------
This script proves the AEC algorithm works mathematically.

1. Generates "Reference" (Simulated Music/TTS)
2. Generates "Mic Input" = Reference (Delayed) + Noise (Subway background)
3. Runs AEC
4. Calculates "Echo Reduction" (ERLE) in dB

If the output energy is significantly lower than the input echo energy, AEC is working.
"""
import numpy as np
from aec_processor import SoftwareAEC

def test_synthetic_aec():
    print("🧪 Running Synthetic AEC Test (No Mic)...")
    
    # 1. Config
    sample_rate = 16000
    duration = 5.0 # seconds
    delay_ms = 200 # simulated system latency
    
    # 2. Generate Signals
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Reference Signal (Loud Music)
    # Mix of low and high frequencies
    reference_signal = (
        np.sin(2 * np.pi * 200 * t) + 
        np.sin(2 * np.pi * 440 * t) * 0.5 +
        np.random.normal(0, 0.1, len(t))
    ) * 10000 
    
    # Echo Signal (Delayed Reference)
    delay_samples = int(sample_rate * delay_ms / 1000)
    echo_signal = np.roll(reference_signal, delay_samples)
    echo_signal[:delay_samples] = 0 # silence at start
    
    # Background Noise (Subway rumble)
    noise_signal = np.random.normal(0, 500, len(t))
    
    # Mic Input = Echo + Noise (No user speech)
    # We want AEC to remove Echo and leave only Noise (ideally)
    mic_signal = (echo_signal * 0.8) + noise_signal
    
    # Convert to int16 bytes
    ref_bytes = reference_signal.astype(np.int16).tobytes()
    mic_bytes = mic_signal.astype(np.int16).tobytes()
    
    # 3. Setup AEC
    aec = SoftwareAEC(sample_rate=sample_rate)
    
    # Important: Set the delay compensation to match our simulation
    # In real life, we estimate this. Here we match it perfectly to test the algorithm logic.
    aec.set_bluetooth_delay(delay_ms)
    
    # 4. Process
    print(f"   -> Processing {duration}s of audio...")
    frame_size = 320 # 20ms
    processed_audio = bytearray()
    
    # Reset internal buffer
    aec.reset()
    
    # Pre-fill silence to align alignment (SoftwareAEC does this in init, but let's be sure)
    # Note: Our SoftwareAEC class handles the delay buffer internally
    
    cursor = 0
    total_len = len(mic_bytes)
    
    while cursor < total_len:
        # Get chunks
        chunk_mic = mic_bytes[cursor:cursor+frame_size*2]
        if len(chunk_mic) < frame_size*2: break
        
        # Feed Reference (Timed correctly)
        # The reference corresponding to this mic chunk is technically valid NOW
        # But AEC has a buffer. We just feed it continuously.
        chunk_ref = ref_bytes[cursor:cursor+frame_size*2]
        aec.feed_reference(chunk_ref)
        
        # Process
        out = aec.cancel_echo(chunk_mic)
        processed_audio.extend(out)
        
        cursor += frame_size*2
        
    # 5. Measure Results
    # Convert output to numpy
    output_signal = np.frombuffer(processed_audio, dtype=np.int16)
    
    # Calculate Energy
    # Echo Energy (Input)
    echo_energy_db = 10 * np.log10(np.mean(mic_signal[:len(output_signal)]**2))
    
    # Residual Energy (Output)
    # Ideally should be close to Noise Floor
    output_energy_db = 10 * np.log10(np.mean(output_signal**2))
    
    noise_floor_db = 10 * np.log10(np.mean(noise_signal**2))
    
    print("\n📊 Results:")
    print(f"   Input Level (Echo+Noise): {echo_energy_db:.2f} dB")
    print(f"   Noise Floor (Target):     {noise_floor_db:.2f} dB")
    print(f"   Output Level (Result):    {output_energy_db:.2f} dB")
    
    improvement = echo_energy_db - output_energy_db
    print(f"   ----------------------------------------")
    print(f"   📉 Echo Reduction:        {improvement:.2f} dB")
    
    if improvement > 10:
        print("   ✅ PASS: Significant echo reduction detected.")
    else:
        print("   ⚠️ FAIL: Weak echo reduction. Algorithm config may need tuning.")

if __name__ == "__main__":
    test_synthetic_aec()
