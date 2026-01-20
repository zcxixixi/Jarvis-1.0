#!/usr/bin/env python3
"""
JARVIS with Gemini 2.0 Live API
真正的实时语音对话 - 端到端音频模型
"""
import asyncio
import pyaudio
import sys
from google import genai

# Configuration
API_KEY = "AIzaSyC2WXgevKwJ42YWBmyMR8cunGBu5XiX59Y"
MODEL = "gemini-2.0-flash-exp"

# Audio settings
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# System instruction
SYSTEM_INSTRUCTION = """你是贾维斯（JARVIS），一个高级AI语音助手。
请用简短、自然的中文回复。像朋友一样对话，不要太正式。
回复要简洁，通常1-2句话即可。"""

class GeminiLiveVoice:
    def __init__(self):
        self.client = genai.Client(api_key=API_KEY)
        self.audio = pyaudio.PyAudio()
        self.audio_queue = asyncio.Queue()
        
    async def listen_for_audio(self):
        """Capture audio from microphone and send to Gemini"""
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SEND_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
        
        print("🎤 麦克风已开启，请开始说话...")
        
        while True:
            try:
                data = await asyncio.to_thread(
                    stream.read, CHUNK_SIZE, exception_on_overflow=False
                )
                self.audio_queue.put_nowait(data)
            except Exception as e:
                print(f"麦克风错误: {e}")
                break
    
    async def send_audio(self, session):
        """Send audio chunks to Gemini"""
        while True:
            data = await self.audio_queue.get()
            await session.send(input={"data": data, "mime_type": "audio/pcm"})
    
    async def play_response(self, session):
        """Receive and play Gemini's audio response"""
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        )
        
        async for response in session.receive():
            if response.data:
                # Play audio directly
                await asyncio.to_thread(stream.write, response.data)
            
            if response.text:
                print(f"📝 {response.text}", end="", flush=True)
            
            if response.server_content and response.server_content.turn_complete:
                print()  # New line after turn completes
    
    async def run(self):
        """Main conversation loop"""
        print("🚀 Jarvis Gemini Live 正在启动...")
        print("=" * 50)
        
        config = {
            "generation_config": {
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": "Aoede"  # Natural voice
                        }
                    }
                }
            },
            "system_instruction": SYSTEM_INSTRUCTION
        }
        
        async with self.client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ 已连接到 Gemini Live!")
            print("💬 现在可以直接对话了，按 Ctrl+C 退出")
            print("=" * 50)
            
            # Run tasks concurrently (Python 3.9 compatible)
            await asyncio.gather(
                self.listen_for_audio(),
                self.send_audio(session),
                self.play_response(session)
            )
    
    def cleanup(self):
        """Cleanup resources"""
        self.audio.terminate()

async def main():
    voice = GeminiLiveVoice()
    try:
        await voice.run()
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        voice.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
