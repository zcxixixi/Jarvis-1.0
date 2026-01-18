
import os
import time
import pyaudio
import base64
from cartesia import Cartesia

API_KEY = "sk_car_f5k7zJEV3AiNorLHgio9M9"
VOICE_ID = "a0e99841-438c-4a64-b679-ae501e7d6091"
MODEL_ID = "sonic-multilingual" 

client = Cartesia(api_key=API_KEY)
p = pyaudio.PyAudio()

def play_test(name, encoding, rate, fmt, text):
    print(f"\n🧪 Testing: [{name}]")
    try:
        stream = p.open(format=fmt, channels=1, rate=rate, output=True)
        
        output = client.tts.sse(
            model_id=MODEL_ID,
            voice={"mode": "id", "id": VOICE_ID},
            transcript=text,
            output_format={
                "container": "raw",
                "encoding": encoding,
                "sample_rate": rate,
            }
        )
        
        print("   ▶️ Playing...", end="", flush=True)
        count = 0
        for chunk in output:
             payload = None
             if hasattr(chunk, "data"): payload = chunk.data
             elif hasattr(chunk, "audio"): payload = chunk.audio
             elif isinstance(chunk, dict): payload = chunk.get("data") or chunk.get("audio")
             else: payload = chunk
             
             if payload:
                 if isinstance(payload, str):
                     try: payload = base64.b64decode(payload)
                     except: pass
                 stream.write(payload)
                 count += 1
        
        print(f" Done! ({count} chunks)")
        time.sleep(1)
        stream.stop_stream()
        stream.close()
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("🔊 Testing 24kHz & 22kHz for CHINESE ...")

# 1. 24k Int16
play_test("24k - Int16", "pcm_s16le", 24000, pyaudio.paInt16, "你好，我是贾维斯。")

# 2. 24k Float32
play_test("24k - Float32", "pcm_f32le", 24000, pyaudio.paFloat32, "你好，我是贾维斯。")

# 3. 22.05k Int16 (Another common fallback)
play_test("22k - Int16", "pcm_s16le", 22050, pyaudio.paInt16, "你好，我是贾维斯。")

p.terminate()
