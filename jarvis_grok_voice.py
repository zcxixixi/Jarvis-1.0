#!/usr/bin/env python3
"""
JARVIS with xAI Grok Voice Agent API
真正的实时语音对话 - 端到端音频
"""
import asyncio
import websockets
import json
import base64
import pyaudio
from rich.console import Console

console = Console()

# Configuration - Use environment variable for API key
import os
API_KEY = os.getenv("XAI_API_KEY", "your-xai-api-key-here")
WS_URL = "wss://api.x.ai/v1/realtime"
MODEL = "grok-2-public"

# Audio settings
SEND_SAMPLE_RATE = 24000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

SYSTEM_INSTRUCTION = """你是贾维斯（JARVIS），一个高级AI语音助手。
请用**低沉、稳重的男声**风格回答。
像钢铁侠的管家一样，用简短、专业的中文回复。
严禁使用女性化语气。"""

class GrokVoice:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.running = True
        self.is_speaking = False  # 当 Grok 说话时暂停录音
        
    async def connect(self):
        """Connect to Grok Voice API"""
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        console.print("🚀 正在连接到 Grok Voice...", style="yellow")
        
        async with websockets.connect(WS_URL, additional_headers=headers) as ws:
            console.print("✅ 已连接到 Grok Voice!", style="bold green")
            
            # Send session configuration
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": SYSTEM_INSTRUCTION,
                    "voice": "onyx",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.2,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 800
                    }
                }
            }
            await ws.send(json.dumps(session_config))
            
            console.print("💬 现在可以直接对话了，按 Ctrl+C 退出", style="cyan")
            console.print("=" * 50)
            
            # Run tasks concurrently
            await asyncio.gather(
                self.send_audio(ws),
                self.receive_audio(ws)
            )
    
    async def send_audio(self, ws):
        """Capture and send audio to Grok"""
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SEND_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
        
        console.print("🎤 麦克风已开启", style="dim")
        
        try:
            chunk_count = 0
            while self.running:
                data = await asyncio.to_thread(
                    stream.read, CHUNK_SIZE, exception_on_overflow=False
                )
                
                # Debug: show audio level every 50 chunks
                chunk_count += 1
                if chunk_count % 50 == 0:
                    import numpy as np
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    level = np.abs(audio_data).mean()
                    console.print(f"🎤 音量: {level:.0f}", style="dim", end="\r")
                
                # 如果 Grok 正在说话，不发送音频（避免回声）
                if self.is_speaking:
                    continue
                
                # Encode audio as base64
                audio_b64 = base64.b64encode(data).decode('utf-8')
                
                # Send audio event
                event = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_b64
                }
                await ws.send(json.dumps(event))
                
        except Exception as e:
            console.print(f"麦克风错误: {e}", style="red")
        finally:
            stream.stop_stream()
            stream.close()
    
    async def receive_audio(self, ws):
        """Receive and play audio from Grok"""
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        )
        
        try:
            async for message in ws:
                event = json.loads(message)
                event_type = event.get("type", "")
                
                # Debug: print all event types
                if event_type not in ["input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped", "session.updated", "session.created"]:
                    console.print(f"[DEBUG] 事件: {event_type}", style="dim magenta")
                
                if event_type == "response.output_audio.delta":
                    # Play audio
                    audio_b64 = event.get("delta", "")
                    if audio_b64:
                        audio_data = base64.b64decode(audio_b64)
                        console.print(f"🔊 播放音频 ({len(audio_data)} bytes)", style="dim")
                        await asyncio.to_thread(stream.write, audio_data)
                
                elif event_type == "response.output_audio_transcript.delta":
                    # Print transcript
                    text = event.get("delta", "")
                    if text:
                        console.print(text, end="", style="cyan")
                
                elif event_type == "response.output_audio_transcript.done":
                    console.print()  # New line
                
                elif event_type == "input_audio_buffer.speech_started":
                    console.print("👂 听到了...", style="dim")
                
                elif event_type == "input_audio_buffer.speech_stopped":
                    console.print("🔄 处理中...", style="dim")
                
                elif event_type == "response.created":
                    self.is_speaking = True  # 开始说话，暂停录音
                    console.print("💬 回复中...", style="green")
                
                elif event_type == "response.done":
                    self.is_speaking = False  # 说完了，恢复录音
                    console.print("", style="")  # Done
                
                elif event_type == "session.created":
                    console.print("📡 会话已创建", style="dim")
                
                elif event_type == "session.updated":
                    console.print("⚙️  会话已配置", style="dim")
                
                elif event_type == "error":
                    error = event.get("error", {})
                    console.print(f"❌ 错误: {error.get('message', error)}", style="red")
                    
        except Exception as e:
            console.print(f"接收错误: {e}", style="red")
        finally:
            stream.stop_stream()
            stream.close()
    
    def cleanup(self):
        self.running = False
        self.audio.terminate()

async def main():
    voice = GrokVoice()
    try:
        await voice.connect()
    except KeyboardInterrupt:
        console.print("\n👋 再见!", style="cyan")
    except Exception as e:
        console.print(f"错误: {e}", style="red")
        import traceback
        traceback.print_exc()
    finally:
        voice.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
