
import asyncio
import os
import json
import uuid
import time
from jarvis_assistant.services.doubao.tts_bidirection import BidirectionalTTS

async def test_tts():
    print("🧪 Starting TTS 2.0 Diagnostic Test...")
    tts = BidirectionalTTS()
    
    try:
        print("🔗 Connecting...")
        await tts.connect()
        
        test_phrases = [
            "[coldness] 先生，您终于回来了。我的检测系统显示您的精神状态略显疲惫。",
            "[happy] 哈哈，这真是一个绝妙的笑话，虽然逻辑上漏洞百出。",
            "[angry] 先生，我建议您在下次操作前先读完说明书。"
        ]
        
        for phrase in test_phrases:
            print(f"🗣️ Sending: {phrase}")
            await tts.send_text(phrase)
            
            print("🔊 Receiving audio...")
            chunk_count = 0
            async for chunk in tts.audio_stream():
                if chunk:
                    chunk_count += 1
                    if chunk_count == 1:
                        print("✅ First audio chunk received!")
            
            print(f"🏁 Phrase finished. Received {chunk_count} chunks.")
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"❌ Test Failed: {e}")
    finally:
        await tts.close()
        print("🔌 Connection closed.")

if __name__ == "__main__":
    asyncio.run(test_tts())
