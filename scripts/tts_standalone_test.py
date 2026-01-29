import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis_assistant.services.doubao.tts_bidirection import BidirectionalTTS
from jarvis_assistant.services.doubao.protocol import EventType
from jarvis_assistant.services.tools.info_tools import get_stock_price

async def test_tts_class():
    print("🚀 Starting Standalone TTS Class Test...")
    
    # 1. Get Real Content
    print("   🔍 Fetching Apple Stock Price...")
    stock_text = await get_stock_price("苹果")
    print(f"   📄 Content: {stock_text}")
    
    tts = BidirectionalTTS()
    print(f"🔧 Loaded Params: AppID={tts.appid}, Resource={tts.resource_id}, Speaker={tts.voice_type}")
    
    try:
        print("   ⏳ Connecting to TTS...")
        await tts.connect()
        
        print("   ⏳ Starting Session...")
        await tts.start_session()
        print("   ✅ Session Started")
        
        text = stock_text
        print(f"   🎙️ Sending Text: {text}")
        await tts.send_text(text)
        
        import subprocess
        
        # Use afplay implementation or direct pipe to player
        # Since afplay expects a file, we might use a simple pyAudio stream for true realtime
        # But for simplicity in script, let's use PyAudio as it's already in dependencies
        import pyaudio
        
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=24000,
                        output=True)

        print("   🔊 Playing audio stream...")
        chunk_count = 0
        
        async for chunk in tts.audio_stream():
            if chunk:
                stream.write(chunk)
                chunk_count += 1
                if chunk_count % 10 == 0:
                    print(".", end="", flush=True)
        
        print(f"\n   ✅ Finished! Played {chunk_count} chunks.")
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await tts.close()

if __name__ == "__main__":
    asyncio.run(test_tts_class())
