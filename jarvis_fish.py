#!/usr/bin/env python3
"""
JARVIS with Fish Audio & Groq
全免费/低成本方案：
- LLM: Groq (Llama3 70B) - 极速免费
- TTS: Fish Audio - 高质量克隆
- STT: Local Whisper - 本地免费
"""
import os
import asyncio
import time
import requests
import pyaudio
import wave
import numpy as np
from rich.console import Console
from faster_whisper import WhisperModel
import io
import edge_tts
from pydub import AudioSegment
from pydub.playback import play

# 导入配置
from config import Config
from jarvis_core import JarvisCore

console = Console()

# TTS Voice
TTS_VOICE = "zh-CN-YunxiNeural" # 男声 

class JarvisFish:
    def __init__(self):
        self.console = Console()
        self.core = JarvisCore()
        
        # Audio settings
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.p = pyaudio.PyAudio()
        
        # VAD settings
        self.VAD_THRESHOLD = 500  # Voice activity threshold
        self.SILENCE_LIMIT = 2    # Seconds of silence to stop recording
        
        self.VAD_THRESHOLD = 500  # Voice activity threshold
        self.SILENCE_LIMIT = 2    # Seconds of silence to stop recording
        
        # Init Whisper
        self.console.print("Loading Whisper model...", style="yellow")
        self.stt_model = WhisperModel("base", device="cpu", compute_type="int8")
        self.console.print("✅ Whisper ready", style="green")

    def get_input(self):
        """Get text input from user"""
        try:
            text = self.console.input("[bold green]You: [/]")
            return text
        except (EOFError, KeyboardInterrupt):
            return None

    def speak(self, text):
        """Speak using Edge TTS"""
        if not text:
            return
            
        self.console.print("🔊 Generating audio...", style="dim")
        try:
            communicate = edge_tts.Communicate(text, TTS_VOICE)
            # Edge TTS needs asyncio, but we are already in sync loop
            # So we create a small async routine
            
            async def _get_audio():
                mp3_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        mp3_data += chunk["data"]
                return mp3_data

            mp3_data = asyncio.run(_get_audio())
            
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
            play(audio)
            
        except Exception as e:
            self.console.print(f"Edge TTS Error: {e}", style="red")

    def run(self):
        self.console.print("🤖 Jarvis Text-to-Voice Mode (Edge TTS)", style="bold purple")
        try:
            while True:
                # 1. Get Text Input
                text = self.get_input()
                if text is None or text.strip().lower() in ['exit', 'quit']:
                    break
                
                if not text.strip():
                    continue
                    
                # 2. Get LLM response (streaming)
                print("Jarvis: ", end="", flush=True)
                full_response = ""
                
                # Collect response first for TTS
                stream = self.core.chat_stream(text)
                for chunk in stream:
                    print(chunk, end="", flush=True)
                    full_response += chunk
                print()
                
                # 3. Speak
                self.speak(full_response)
                
        except KeyboardInterrupt:
            self.console.print("\n👋 Goodbye!", style="cyan")
        finally:
            self.p.terminate()

if __name__ == "__main__":
    if not Config.GROQ_API_KEY:
        console.print("❌ Missing GROQ_API_KEY in .env", style="red")
        exit(1)
        
    jarvis = JarvisFish()
    jarvis.run()
