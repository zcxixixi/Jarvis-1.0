#!/usr/bin/env python3
"""
JARVIS 本地语音版 - 使用 macOS 自带 TTS
完全离线运行，无需网络
"""
import asyncio
import subprocess
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

class JarvisLocal:
    def __init__(self):
        console.print("🔧 正在初始化...", style="yellow")
        
        # Initialize Whisper model (local STT)
        console.print("📥 加载语音识别模型...", style="dim")
        self.whisper = WhisperModel("base", device="cpu", compute_type="int8")
        console.print("✅ Whisper 已加载", style="green")
        
        # Initialize LLM
        self.jarvis = JarvisCore()
        console.print(f"✅ LLM 已加载: {self.jarvis.model}", style="green")
        
        # Audio settings
        self.sample_rate = 16000
        self.chunk_size = 1024
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        
        console.print("✅ 系统就绪！", style="bold green")

    def speak(self, text):
        """使用 macOS say 命令朗读"""
        if not text.strip():
            return
        # 使用中文语音 Tingting
        subprocess.run(["say", "-v", "Tingting", text], check=True)

    def record_audio(self, duration=8, silence_threshold=500, silence_duration=1.5):
        """录制音频"""
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
            
            audio_data = np.frombuffer(data, dtype=np.int16)
            level = np.abs(audio_data).mean()
            
            if level > silence_threshold:
                has_speech = True
                silent_chunks = 0
            else:
                silent_chunks += 1
            
            if has_speech and silent_chunks > silence_chunks_threshold:
                break
        
        stream.stop_stream()
        stream.close()
        
        if not has_speech:
            return None
        
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
        """本地语音识别"""
        console.print("🔄 识别中...", style="dim")
        
        segments, info = self.whisper.transcribe(audio_file, language="zh")
        text = "".join([segment.text for segment in segments]).strip()
        
        if os.path.exists(audio_file):
            os.remove(audio_file)
        
        return text

    def listen(self):
        """监听并识别"""
        audio_file = self.record_audio()
        
        if not audio_file:
            console.print("🤷 没听到...", style="dim")
            return None
        
        text = self.transcribe(audio_file)
        
        if text:
            console.print(f"🗣️  你: {text}", style="bold green")
        else:
            console.print("🤷 没听清...", style="dim")
            
        return text if text else None

    def chat_and_speak(self, user_input):
        """对话并朗读"""
        console.print("💭 思考中...", style="dim")
        
        # 使用流式响应并按句子朗读
        sentence_buffer = ""
        sentence_endings = re.compile(r'[。！？.!?\n]')
        
        for chunk in self.jarvis.chat_stream(user_input):
            sentence_buffer += chunk
            console.print(chunk, end="", style="cyan")
            
            while sentence_endings.search(sentence_buffer):
                match = sentence_endings.search(sentence_buffer)
                if match:
                    end_pos = match.end()
                    sentence = sentence_buffer[:end_pos].strip()
                    sentence_buffer = sentence_buffer[end_pos:]
                    
                    if sentence:
                        self.speak(sentence)
        
        console.print()
        
        if sentence_buffer.strip():
            self.speak(sentence_buffer.strip())

    def run(self):
        console.print("\n🚀 Jarvis 本地语音模式 (macOS TTS)", style="bold green")
        console.print("💬 开始说话吧！说'退出'结束", style="cyan")
        
        while True:
            try:
                user_input = self.listen()
                
                if not user_input:
                    continue
                    
                if any(word in user_input for word in ['退出', '再见', '拜拜']):
                    self.speak("好的，再见。")
                    break
                
                self.chat_and_speak(user_input)
                
            except KeyboardInterrupt:
                console.print("\n👋 再见！", style="cyan")
                break
            except Exception as e:
                console.print(f"❌ 错误: {e}", style="red")
                if Config.DEBUG:
                    import traceback
                    traceback.print_exc()
    
    def __del__(self):
        try:
            self.audio.terminate()
        except:
            pass

if __name__ == "__main__":
    client = JarvisLocal()
    client.run()
