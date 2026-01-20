"""
Noise Suppression Test Script
----------------------------
Since you are wearing headphones, Echo Cancellation (AEC) isn't needed (no sound leaks to mic).
However, our module also enables "Noise Suppression" (denoiser) which is great for the subway!

This script tests ONLY the noise suppression:
1. Records your noisy environment (Subway).
2. Runs it through the processor.
3. Saves raw vs clean audio.

Usage:
    python test_noise_suppression.py
"""
import time
import wave
import pyaudio
import sys
from aec_processor import SoftwareAEC

# Configuration
SAMPLE_RATE = 16000
FRAME_SIZE = 320 # 20ms
DURATION = 5 # Record 5 seconds of noise

def save_wav(filename, data, channels=1, rate=16000):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(2)
    wf.setframerate(rate)
    wf.writeframes(b''.join(data))
    wf.close()
    print(f"   -> Saved: {filename}")

def main():
    print("🎧 Noise Suppression Test (Headphones Mode)")
    print("-----------------------------------------")
    print("Since you have headphones on, we will test if Jarvis can filter out background noise.")
    
    aec = SoftwareAEC(sample_rate=SAMPLE_RATE)
    p = pyaudio.PyAudio()
    
    mic = p.open(format=pyaudio.paInt16,
                 channels=1,
                 rate=SAMPLE_RATE,
                 input=True,
                 frames_per_buffer=FRAME_SIZE)
                 
    print("\n🔴 Recording 5 seconds of background noise... (Don't speak, just let it record the subway)")
    time.sleep(1)
    
    raw_frames = []
    clean_frames = []
    
    num_chunks = int(SAMPLE_RATE * DURATION / (FRAME_SIZE // 2))
    
    try:
        for i in range(num_chunks):
            # Read Mic
            raw_chunk = mic.read(FRAME_SIZE, exception_on_overflow=False)
            raw_frames.append(raw_chunk)
            
            # Process (AEC module does Noise Suppression too if configured)
            # We don't feed reference (since headphones = no reference sound in mic)
            clean_chunk = aec.cancel_echo(raw_chunk)
            clean_frames.append(clean_chunk)
            
            if i % 10 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        pass
    finally:
        mic.stop_stream()
        mic.close()
        p.terminate()
        
    print("\n\n✅ Done!")
    save_wav("test_raw_noise.wav", raw_frames)
    save_wav("test_clean_noise.wav", clean_frames)
    
    print("\n🔍 How to check:")
    print("1. Listen to 'test_raw_noise.wav' (Should hear loud subway noise)")
    print("2. Listen to 'test_clean_noise.wav' (Should be quieter)")

if __name__ == "__main__":
    main()
