import asyncio
import os
import sys
from dotenv import load_dotenv

# Add jarvis_assistant to path
sys.path.append("/Users/kaijimima1234/Desktop/jarvis")

from jarvis_assistant.services.doubao.tts_bidirection import BidirectionalTTS

async def test_bidir():
    print("Testing Bidirectional TTS...")
    tts = BidirectionalTTS()
    try:
        await tts.connect()
        print("Connected.")
        
        await tts.start_session()
        print("Session started.")
        
        # Simulating streaming text
        text = "你好，我是贾维斯。很高兴为您服务。"
        print(f"Sending text: {text}")
        await tts.send_text(text)
        await tts.finish_session()
        
        print("Waiting for audio...")
        count = 0
        total_size = 0
        async for chunk in tts.audio_stream():
            count += 1
            total_size += len(chunk)
            if count % 10 == 0:
                print(f"Received {count} chunks, total size: {total_size}")
        
        print(f"Test Success! Received {count} chunks, total {total_size} bytes.")
        
    except Exception as e:
        print(f"Test Failed: {e}")
    finally:
        await tts.close()

if __name__ == "__main__":
    asyncio.run(test_bidir())
