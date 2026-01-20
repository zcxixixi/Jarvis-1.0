"""
Real-time AEC Verification Script
--------------------------------
This script verifies the Acoustic Echo Cancellation (AEC) module in isolation.

It does the following:
1. Generates a test sound (White Noise + Sine Wave tones).
2. Plays this sound through the speakers (The "Echo" source).
3. Simultaneously records from the microphone.
4. Processes the recording through the Software AEC module.
5. Saves two files for comparison:
   - 'raw_recording.wav': What the mic heard (Music + Your Voice)
   - 'clean_recording_aec.wav': Result after AEC (Should be mostly Your Voice)

Usage:
    python test_aec_realtime.py
"""
import time
import wave
import struct
import math
import pyaudio
import numpy as np
from aec_processor import SoftwareAEC

# Configuration
SAMPLE_RATE = 16000
FRAME_SIZE = 320 # 20ms
DURATION = 10 # Seconds to record
OUTPUT_FILENAME_RAW = "raw_recording.wav"
OUTPUT_FILENAME_AEC = "clean_recording_aec.wav"

def generate_tone_music(duration, rate):
    """Synthetic Music (Tonal + Beat)"""
    t = np.linspace(0, duration, int(rate * duration), endpoint=False)
    noise = np.random.normal(0, 0.2, len(t))
    freq = np.linspace(200, 800, len(t))
    tone = np.sin(2 * np.pi * freq * t) * 0.5
    beat = np.sin(2 * np.pi * 2 * t) 
    audio = (noise + tone) * beat * 0.5
    return audio * 32767

def generate_tone_speech(duration, rate):
    """Synthetic Speech-like (Bursting Noise)"""
    t = np.linspace(0, duration, int(rate * duration), endpoint=False)
    # Modulate white noise with speech-like envelope (4Hz syllables)
    envelope = (np.sin(2 * np.pi * 4 * t) + 1) / 2
    envelope = envelope * envelope # Sharpen peak
    noise = np.random.normal(0, 0.8, len(t))
    # Low-pass filter effect (simple)
    audio = noise * envelope
    return audio * 32767

def generate_tone_sweep(duration, rate):
    """Frequency Sweep (Chirp) - Good for rigorous testing"""
    t = np.linspace(0, duration, int(rate * duration), endpoint=False)
    # Sweep 100Hz -> 4000Hz
    k = (4000 - 100) / duration
    audio = np.sin(2 * np.pi * (100 * t + 0.5 * k * t**2)) * 0.8
    return audio * 32767

def get_test_audio(choice, duration=10, rate=16000):
    if choice == "1": audio = generate_tone_music(duration, rate)
    elif choice == "2": audio = generate_tone_speech(duration, rate)
    elif choice == "3": audio = generate_tone_sweep(duration, rate)
    else: audio = generate_tone_music(duration, rate)
    
    return audio.astype(np.int16).tobytes()

def save_wav(filename, data, channels=1, rate=16000):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(2) # 16-bit
    wf.setframerate(rate)
    wf.writeframes(b''.join(data))
    wf.close()
    print(f"   -> Saved: {filename}")

def main():
    print("🎤 AEC Isolation Test")
    print("-------------------")
    
    # 1. Initialize AEC
    print("1. Initializing AEC (Software)...")
    aec = SoftwareAEC(sample_rate=SAMPLE_RATE, frame_size=FRAME_SIZE//2)
    
    # 2. Select Audio
    print("\n🎵 Select Test Audio Type:")
    print("   1. Synthetic Music (Tones + Beat) [Default]")
    print("   2. Simulated Speech (Bursting Noise)")
    print("   3. Frequency Sweep (Chirp 100Hz->4kHz)")
    choice = input("   Enter choice (1-3): ")
    
    print("2. Generating Test Signal...")
    reference_data = get_test_audio(choice, DURATION, SAMPLE_RATE)
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    input("⚠️ Press Enter to START (Make sure speakers are ON and Volume is UP)...")
    print("\n🔴 Recording & Playing... SPEAK something now! (e.g. 'Testing 1 2 3')")
    
    try:
        # Open Streams
        # Output stream (Speaker)
        player = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=SAMPLE_RATE,
                        output=True)
                        
        # Input stream (Mic)
        recorder = p.open(format=pyaudio.paInt16,
                          channels=1,
                          rate=SAMPLE_RATE,
                          input=True,
                          frames_per_buffer=FRAME_SIZE)
        
        raw_frames = []
        clean_frames = []
        
        # We process in chunks
        chunk_size = FRAME_SIZE # bytes (320 bytes = 160 samples)
        total_chunks = len(reference_data) // chunk_size
        
        start_time = time.time()
        
        # Pre-feed some reference to account for buffering
        # aec.feed_reference(reference_data[:3200]) 
        
        for i in range(total_chunks):
            # 1. Get current reference chunk
            offset = i * chunk_size
            ref_chunk = reference_data[offset:offset+chunk_size]
            
            # 2. Play it (Speaker)
            player.write(ref_chunk)
            
            # 3. Feed it to AEC (Reference)
            # IMPORTANT: We feed the AEC *before* or *at same time* as playback
            aec.feed_reference(ref_chunk)
            
            # 4. Read Mic (Input)
            # This read will block until frames are available
            mic_chunk = recorder.read(FRAME_SIZE, exception_on_overflow=False)
            raw_frames.append(mic_chunk)
            
            # 5. Cancel Echo
            clean_chunk = aec.cancel_echo(mic_chunk)
            clean_frames.append(clean_chunk)
            
            # Progress bar
            if i % 10 == 0:
                sys.stdout.write(f"\r   Progress: {int((i/total_chunks)*100)}%")
                sys.stdout.flush()
                
        print("\n✅ Recording Complete!")
        
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        player.stop_stream()
        player.close()
        recorder.stop_stream()
        recorder.close()
        p.terminate()
        
    # 3. Save Files
    print("\n3. Saving Output Files...")
    save_wav(OUTPUT_FILENAME_RAW, raw_frames, rate=SAMPLE_RATE)
    save_wav(OUTPUT_FILENAME_AEC, clean_frames, rate=SAMPLE_RATE)
    
    print("\n🔍 Verification Guide:")
    print(f"1. Listen to '{OUTPUT_FILENAME_RAW}' -> Should hear loud music + your voice.")
    print(f"2. Listen to '{OUTPUT_FILENAME_AEC}' -> Music should be reduced, your voice clearer.")

if __name__ == "__main__":
    import sys
    main()
