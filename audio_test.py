
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

def play_test(name, encoding, rate, fmt, text, lang_code=None):
    print(f"\n🧪 Testing Case: [{name}]")
    print(f"   Format: {encoding} @ {rate}Hz")
    print(f"   Text: '{text}' (Lang: {lang_code})")
    
    try:
        stream = p.open(format=fmt, channels=1, rate=rate, output=True)
        
        # Build Voice Object
        voice_settings = {"mode": "id", "id": VOICE_ID}
        # Some SDK versions allow specifying experimental language settings here or in model settings
        # Actually Cartesia auto-detects, but let's see.
        
        start_t = time.time()
        output = client.tts.sse(
            model_id=MODEL_ID,
            voice=voice_settings,
            transcript=text,
            output_format={
                "container": "raw",
                "encoding": encoding,
                "sample_rate": rate,
            },
            # language=lang_code # Uncomment if SDK supports explicit language param
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
        time.sleep(0.5)
        stream.stop_stream()
        stream.close()
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("🔊 Starting Detailed Sound & Language Test...")

# 1. English - Float32 (Reference)
play_test("English - Float32", "pcm_f32le", 44100, pyaudio.paFloat32, "This is Jarvis voice check.", "en")

# 2. Chinese - Float32 
play_test("Chinese - Float32", "pcm_f32le", 44100, pyaudio.paFloat32, "你好，我是贾维斯。", "zh")

# 3. English - Int16 (Reference)
play_test("English - Int16", "pcm_s16le", 44100, pyaudio.paInt16, "This is Jarvis voice check.", "en")

# 4. Chinese - Int16
play_test("Chinese - Int16", "pcm_s16le", 44100, pyaudio.paInt16, "你好，我是贾维斯。", "zh")

p.terminate()
print("\n✅ Test Complete.")
print("Which one sounded best? (Float32 vs Int16? English vs Chinese?)")
