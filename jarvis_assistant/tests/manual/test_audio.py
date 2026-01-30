import pyaudio
import wave
import time
import math
import audioop
import sys

# Configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "test_audio_loop.wav"

def test_audio_loop():
    p = pyaudio.PyAudio()

    print("="*50)
    print("🎤 AUDIO HARDWARE DIAGNOSTIC")
    print("="*50)

    # 1. List Devices
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    print(f"Found {numdevices} audio devices:")
    for i in range(0, numdevices):
        dev = p.get_device_info_by_host_api_device_index(0, i)
        if dev.get('maxInputChannels') > 0:
            print(f"  [Input]  ID {i}: {dev.get('name')}")
        if dev.get('maxOutputChannels') > 0:
            print(f"  [Output] ID {i}: {dev.get('name')}")

    # 2. Record
    print(f"\n🔴 Recording for {RECORD_SECONDS} seconds... PLEASE SPEAK!")
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    frames = []
    max_energy = 0

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        
        # Calculate energy (RMS)
        rms = audioop.rms(data, 2)
        if rms > max_energy:
            max_energy = rms
        
        # Simple visualizer
        bars = "#" * int((rms / 300))
        sys.stdout.write(f"\rLevel: {rms:5d} |{bars.ljust(50)}|")
        sys.stdout.flush()

    print("\n\n⏹️  Finished recording.")
    stream.stop_stream()
    stream.close()

    # check if silence
    print(f"📊 Max Signal Energy: {max_energy}")
    if max_energy < 100:
        print("❌ ERROR: Microphone signal too low! Is it muted or disconnected?")
    elif max_energy < 500:
        print("⚠️ WARNING: Signal is weak. You might need to speak louder or adjust gain.")
    else:
        print("✅ Signal input looks healthy.")

    # 3. Save
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    print(f"💾 Saved diagnostics to {WAVE_OUTPUT_FILENAME}")

    # 4. Playback
    print(f"\n▶️  Playing back recorded audio...")
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'rb')
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    data = wf.readframes(CHUNK)
    while len(data) > 0:
        stream.write(data)
        data = wf.readframes(CHUNK)

    stream.stop_stream()
    stream.close()
    p.terminate()
    print("\n✅ Audio Loopback Test Complete")

if __name__ == "__main__":
    import sys
    try:
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        
        print(f"🔍 Scanning {numdevices} devices for active audio...")
        
        valid_mic_found = False
        
        for i in range(0, numdevices):
            dev = p.get_device_info_by_host_api_device_index(0, i)
            if dev.get('maxInputChannels') > 0:
                name = dev.get('name')
                print(f"\n[Testing ID {i}: {name}]")
                try:
                    # Supported rates to probe
                    for test_rate in [48000, 44100, 16000]:
                         try:
                            # print(f"    Probing {test_rate}Hz...", end="")
                            stream = p.open(format=FORMAT,
                                            channels=CHANNELS,
                                            rate=test_rate,
                                            input=True,
                                            input_device_index=i,
                                            frames_per_buffer=CHUNK)
                            print(f"  [OK: {test_rate}Hz] ", end="")
                            break
                         except:
                            continue
                    else:
                        raise Exception("No supported sample rate found (tried 48k, 44.1k, 16k)")

                    print(f"\n  🔴 Recording 10s... PLEASE SPEAK LOUDLY OR TAP THE MIC! ...", end="", flush=True)
                    max_e = 0
                    for _ in range(0, int(RATE / CHUNK * 10)):
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        rms = audioop.rms(data, 2)
                        max_e = max(max_e, rms)
                        # Visual feedback
                        if _ % 5 == 0:
                            print(".", end="", flush=True)
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        rms = audioop.rms(data, 2)
                        max_e = max(max_e, rms)
                    
                    stream.stop_stream()
                    stream.close()
                    
                    print(f" Max Energy: {max_e}")
                    if max_e > 500:
                        print(f"  ✅ ACTIVE SIGNAL DETECTED! (ID {i})")
                        valid_mic_found = True
                        # Recommend this one
                        if "USB" in name or not valid_mic_found: 
                             pass # Prefer USB or first working
                except Exception as e:
                    print(f"  ❌ Failed to open: {e}")

        p.terminate()
        
        if not valid_mic_found:
             print("\n❌ NO WORKING MICROPHONE FOUND (All < 500 energy)")
             sys.exit(1)
             
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)
