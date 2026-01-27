import sys
import asyncio
import pyaudio
import numpy as np
import onnxruntime
import openwakeword
import time

print("Step 1: All basic imports finished", flush=True)

try:
    print("Step 2: Initializing PyAudio...", flush=True)
    p = pyaudio.PyAudio()
    print("SUCCESS: PyAudio initialized", flush=True)
except Exception as e:
    print(f"FAILED: PyAudio init: {e}", flush=True)
    sys.exit(1)

try:
    # Use exact params from jarvis_doubao_config.py
    print("Step 3: Opening Output Stream (Device 2, 24kHz)...", flush=True)
    out_stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=24000,
        output=True,
        output_device_index=2
    )
    print("SUCCESS: Output stream opened", flush=True)
    out_stream.close()
except Exception as e:
    print(f"FAILED: Output stream: {e}", flush=True)

try:
    print("Step 4: Opening Input Stream (Device 1, 48kHz)...", flush=True)
    in_stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=48000,
        input=True,
        input_device_index=1,
        frames_per_buffer=1280
    )
    print("SUCCESS: Input stream opened", flush=True)
    in_stream.close()
except Exception as e:
    print(f"FAILED: Input stream: {e}", flush=True)

p.terminate()
print("ALL TESTS COMPLETED", flush=True)
