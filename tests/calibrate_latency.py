"""
Audio Latency Calibrator
------------------------
Measures the Round-Trip Latency (RTL) of your audio system.
This is CRITICAL for good AEC performance.

1. Plays a sharp "BEEP".
2. Records via mic.
3. Finds the peak offset.
4. Tells you exactly what to set 'bluetooth_delay_ms' to.
"""
import time
import wave
import pyaudio
import numpy as np

# Config
SAMPLE_RATE = 16000
FRAME_SIZE = 1024
RECORD_SECONDS = 2.0

def generate_beep(duration=0.1, freq=1000):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Generate simple clean sine wave
    audio = np.sin(2 * np.pi * freq * t) * 0.8
    # Fade in/out to avoid clicking
    envelope = np.ones_like(t)
    envelope[:500] = np.linspace(0, 1, 500)
    envelope[-500:] = np.linspace(1, 0, 500)
    return (audio * envelope * 32767).astype(np.int16).tobytes()

def main():
    print("⏱️  Audio Latency Calibration Tool")
    print("---------------------------------")
    print("Ideally, un-plug headphones and let speaker play into mic.")
    
    p = pyaudio.PyAudio()
    
    # Input Stream
    stream_in = p.open(format=pyaudio.paInt16,
                       channels=1,
                       rate=SAMPLE_RATE,
                       input=True,
                       frames_per_buffer=FRAME_SIZE)
                       
    # Output Stream
    stream_out = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=SAMPLE_RATE,
                        output=True)
                        
    input("⚠️  Press Enter to START MEASUREMENT (Quiet room recommended)...")
    
    # Generate Beep
    beep_data = generate_beep(0.1) # 100ms beep
    
    print("   Playing Beep & Recording...")
    
    frames = []
    
    # 1. Start Recording First
    stream_in.start_stream()
    
    # 2. Play Beep shortly after
    # We record for a bit before playing to catch the start
    pre_record_chunks = 5
    for _ in range(pre_record_chunks):
         frames.append(stream_in.read(FRAME_SIZE, exception_on_overflow=False))
         
    start_time = time.time()
    stream_out.write(beep_data) # Play! (Blocking)
    
    # 3. Continue Recording
    chunks_to_record = int(SAMPLE_RATE * RECORD_SECONDS / FRAME_SIZE)
    for _ in range(chunks_to_record):
        frames.append(stream_in.read(FRAME_SIZE, exception_on_overflow=False))
        
    stream_in.stop_stream()
    stream_in.close()
    stream_out.stop_stream()
    stream_out.close()
    p.terminate()
    
    print("   Analyzing...")
    
    # Convert to numpy
    raw_data = b''.join(frames)
    audio_signal = np.frombuffer(raw_data, dtype=np.int16)
    
    # Find peak
    peak_index = np.argmax(np.abs(audio_signal))
    peak_time_s = peak_index / SAMPLE_RATE
    
    # Calculate Latency
    # We started pre-recording for 'pre_record_chunks' * FRAME_SIZE samples
    # But write() blocks. 
    # Actually, simpler method:
    # The 'write' happened approximately at sample index: pre_record_chunks * FRAME_SIZE
    # So latency is (peak_index - trigger_index)
    
    trigger_index = pre_record_chunks * FRAME_SIZE
    latency_samples = peak_index - trigger_index
    latency_ms = (latency_samples / SAMPLE_RATE) * 1000
    
    print(f"\n📊 Measurement Results:")
    print(f"   Peak detected at sample: {peak_index}")
    print(f"   Estimated Latency: {latency_ms:.1f} ms")
    
    if latency_ms < 0:
        print("   ⚠️  Result seems invalid (Negative latency). Did you hear the beep?")
        print("       Maybe volume too low, or noise triggered peak before beep.")
    elif latency_ms > 1000:
        print("   ⚠️  High latency (>1s). Are you using Bluetooth?")
    else:
        print(f"\n✅ Suggested Config:")
        print(f"   Please update 'aec_processor.py' -> 'bluetooth_delay_ms' to approx: {int(latency_ms)} ms")
        print(f"   (Currently it is default 200ms)")

if __name__ == "__main__":
    main()
