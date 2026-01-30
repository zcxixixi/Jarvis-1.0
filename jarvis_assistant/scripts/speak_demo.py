import asyncio
import os
import sys
import wave
import time
from dotenv import load_dotenv

# Set up paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # .../jarvis_assistant/scripts
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..")) # .../jarvis_assistant
PARENT_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "..")) # .../jarvis

sys.path.insert(0, PARENT_ROOT) # For "from jarvis_assistant..."
sys.path.insert(0, PROJECT_ROOT) # Just in case

print(f"DEBUG: Path inserted: {PARENT_ROOT}")

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

print(f"DEBUG: DOUBAO_APP_ID={os.getenv('DOUBAO_APP_ID')}")
print(f"DEBUG: DOUBAO_SPEECH_TOKEN={os.getenv('DOUBAO_SPEECH_TOKEN')[:5]}..." if os.getenv('DOUBAO_SPEECH_TOKEN') else "DEBUG: DOUBAO_SPEECH_TOKEN=None")
print(f"DEBUG: DOUBAO_TTS_RESOURCE_ID={os.getenv('DOUBAO_TTS_RESOURCE_ID')}")
print(f"DEBUG: TTS_WS_URL={os.getenv('DOUBAO_TTS_WS_URL', 'wss://openspeech.bytedance.com/api/v3/tts/unidirectional/stream')}")

try:
    # Try HTTP first as it might be simpler/more stable for quick test
    from jarvis_assistant.services.doubao.tts_http import synthesize
    USE_HTTP = True
except ImportError:
    from jarvis_assistant.services.doubao.tts_v3 import synthesize_stream
    USE_HTTP = False

async def main():
    text = "系统自检完成。语音合成模块运行正常。随时待命，Cenxi先生。"
    if len(sys.argv) > 1:
        text = sys.argv[1]
        
    print(f"🎤 Generating Audio (HTTP={USE_HTTP}): '{text}'...")
    
    pcm_data = bytearray()
    sr = int(os.getenv("DOUBAO_TTS_SAMPLE_RATE", "24000"))
    
    try:
        start_time = time.time()
        
        if USE_HTTP:
            # HTTP returns all at once
            pcm_data = await synthesize(text)
        else:
            # WS stream
            chunk_count = 0
            async for chunk in synthesize_stream(text):
                chunk_count += 1
                if chunk_count == 1:
                     print(f"⚡ First byte received in {time.time() - start_time:.3f}s")
                pcm_data.extend(chunk)
            
        print(f"✅ Download complete: {len(pcm_data)} bytes in {time.time() - start_time:.3f}s")
        
        # Save to WAV
        out_path = "/tmp/jarvis_speak_test.wav"
        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm_data)
            
        print(f"💾 Saved to {out_path}")
        
        # Play Audio
        print("🔊 Playing audio...")
        ret = os.system(f"afplay {out_path}")
        if ret != 0:
            print("⚠️ 'afplay' failed. Trying 'aplay'...")
            os.system(f"aplay {out_path}")
            
    except Exception as e:
        print(f"❌ Error during synthesis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
