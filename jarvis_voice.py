#!/usr/bin/env python3
"""
JARVIS Voice Interface with Local Whisper + Streaming Response
本地语音识别 + 边生成边说
"""
import asyncio
import edge_tts
import pygame
import os
import tempfile
import re
import numpy as np
from faster_whisper import WhisperModel
import pyaudio
import wave
from jarvis_core import JarvisCore
from config import Config
from rich.console import Console

console = Console()

class JarvisVoice:
    def __init__(self):
        console.print("🔧 正在初始化...", style="yellow")
        
        # Initialize Whisper model (local STT)
        console.print("📥 加载语音识别模型 (首次会下载)...", style="dim")
        self.whisper = WhisperModel("base", device="cpu", compute_type="int8")
        console.print("✅ Whisper 模型已加载", style="green")
        
        # Initialize LLM
        self.jarvis = JarvisCore()
        console.print(f"✅ LLM 已加载: {self.jarvis.model}", style="green")
        
        # TTS settings - 自然女声
        self.voice = "zh-CN-XiaoxiaoNeural"
        
        # Audio settings
        self.sample_rate = 16000
        self.chunk_size = 1024
        
        # Initialize pygame for playback
        pygame.mixer.init()
        
        # Initialize PyAudio for recording
        self.audio = pyaudio.PyAudio()
        
        console.print("✅ 系统就绪！", style="bold green")

    def record_audio(self, duration=5, silence_threshold=500, silence_duration=1.5):
        """Record audio with voice activity detection"""
        console.print("👂 正在聆听...", style="bold cyan")
        
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        frames = []
        silent_chunks = 0
        has_speech = False
        max_chunks = int(self.sample_rate / self.chunk_size * duration)
        silence_chunks_threshold = int(self.sample_rate / self.chunk_size * silence_duration)
        
        for i in range(max_chunks):
            data = stream.read(self.chunk_size, exception_on_overflow=False)
            frames.append(data)
            
            # Calculate audio level
            audio_data = np.frombuffer(data, dtype=np.int16)
            level = np.abs(audio_data).mean()
            
            if level > silence_threshold:
                has_speech = True
                silent_chunks = 0
            else:
                silent_chunks += 1
            
            # Stop if silence detected after speech
            if has_speech and silent_chunks > silence_chunks_threshold:
                break
        
        stream.stop_stream()
        stream.close()
        
        if not has_speech:
            return None
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
            temp_file = fp.name
            
        wf = wave.open(temp_file, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(self.sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return temp_file

    def transcribe(self, audio_file):
        """Transcribe audio using local Whisper"""
        console.print("🔄 识别中...", style="dim")
        
        segments, info = self.whisper.transcribe(audio_file, language="zh")
        text = "".join([segment.text for segment in segments]).strip()
        
        # Clean up
        if os.path.exists(audio_file):
            os.remove(audio_file)
        
        return text

    async def speak_sentence(self, text):
        """Convert a single sentence to speech and play it"""
        if not text.strip():
            return
            
        communicate = edge_tts.Communicate(text, self.voice)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_filename = fp.name
            
        await communicate.save(temp_filename)
        
        try:
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)
        except Exception as e:
            console.print(f"❌ 播放失败: {e}", style="red")
        finally:
            pygame.mixer.music.unload()
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    async def stream_and_speak(self, user_input):
        """Stream LLM response and speak sentences as they complete"""
        console.print("💭 思考中...", style="dim")
        
        sentence_buffer = ""
        full_response = ""
        sentence_endings = re.compile(r'[。！？.!?\n]')
        
        for chunk in self.jarvis.chat_stream(user_input):
            sentence_buffer += chunk
            full_response += chunk
            console.print(chunk, end="", style="cyan")
            
            while sentence_endings.search(sentence_buffer):
                match = sentence_endings.search(sentence_buffer)
                if match:
                    end_pos = match.end()
                    sentence = sentence_buffer[:end_pos].strip()
                    sentence_buffer = sentence_buffer[end_pos:]
                    
                    if sentence:
                        await self.speak_sentence(sentence)
        
        console.print()
        
        if sentence_buffer.strip():
            await self.speak_sentence(sentence_buffer.strip())
        
        return full_response

    def listen(self):
        """Listen and transcribe using local Whisper"""
        audio_file = self.record_audio(duration=10)
        
        if not audio_file:
            console.print("🤷 没听到...", style="dim")
            return None
        
        text = self.transcribe(audio_file)
        
        if text:
            console.print(f"🗣️  你: {text}", style="bold green")
        else:
            console.print("🤷 没听清...", style="dim")
            
        return text if text else None

    async def run(self):
        console.print("\n🚀 Jarvis 本地语音模式已启动", style="bold green")
        console.print("💬 请开始说话...", style="cyan")
        
        while True:
            try:
                user_input = self.listen()
                
                if not user_input:
                    continue
                    
                if any(word in user_input for word in ['退出', '再见', '拜拜']):
                    await self.speak_sentence("好的，再见。")
                    break
                
                await self.stream_and_speak(user_input)
                
            except KeyboardInterrupt:
                console.print("\n👋 再见！", style="cyan")
                break
            except Exception as e:
                console.print(f"❌ 错误: {e}", style="red")
                if Config.DEBUG:
                    import traceback
                    traceback.print_exc()
    
    def __del__(self):
        """Cleanup"""
        try:
            self.audio.terminate()
        except:
            pass

if __name__ == "__main__":
    client = JarvisVoice()
    asyncio.run(client.run())
