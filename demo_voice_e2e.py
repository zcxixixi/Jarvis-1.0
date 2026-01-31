#!/usr/bin/env python3
"""
End-to-End Voice Demo (from SKILL.md)
"""
import asyncio
import json
import wave
import sys
import os
import pyaudio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import time

from jarvis_assistant.services.doubao.websocket import DoubaoRealtimeJarvis
from jarvis_assistant.services.doubao.protocol import DoubaoMessage, MsgType, EventType, SerializationBits
from jarvis_assistant.core.agent import get_agent
from jarvis_assistant.services.doubao.tts_v3 import DoubaoTTSV1

INPUT_WAV = "demo_input.wav"
OUTPUT_WAV = "demo_output.wav"

# 🔥 Global TTS singleton for connection reuse (saves ~125ms per request)
_tts_instance = None

async def get_tts():
    """Get or create persistent TTS connection"""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = DoubaoTTSV1()
    return _tts_instance

# --- COPY FROM SKILL.MD BEGIN ---
class GoldenVoiceDemo(DoubaoRealtimeJarvis):
    def __init__(self):
        super().__init__()
        self.final_text = None
        self.completion_event = asyncio.Event()

    # 🟢 CRITICAL: Disable base class audio loops to prevent interference
    def setup_audio(self): pass
    async def send_audio_loop(self): pass

    async def receive_loop(self):
        print("🎧 Listening for ASR events...")
        async for message in self.ws:
            if not self.is_running: break
            if isinstance(message, str): continue
            
            try:
                msg = DoubaoMessage.from_bytes(message)
                if msg.serialization == SerializationBits.JSON:
                    event = json.loads(msg.payload)
                    # Dialog API returns results in 'results' list
                    if 'results' in event and event['results']:
                        res = event['results'][0]
                        text = res.get('text', '')
                        is_interim = res.get('is_interim', True)
                        if text:
                            print(f"[ASR] {text} {'(interim)' if is_interim else '✅'}")
                            if not is_interim:
                                self.final_text = text
                                print(f"[PERF] 🏁 ASR Final: {time.time():.3f}")  # LOG 1
                                self.completion_event.set()
            except: pass

    async def run_pipeline(self, wav_path):
        # 🟢 CRITICAL: Use create_task, NOT await, or it blocks forever!
        asyncio.create_task(self.connect())
        await asyncio.sleep(2) # Allow connection logic to start
        
        with wave.open(wav_path, 'rb') as wf:
            data = wf.readframes(wf.getnframes())
            
        chunk_size = 3200
        for i in range(0, len(data), chunk_size):
            if self.completion_event.is_set(): break  # ⚡ Break if ASR done
            msg = DoubaoMessage(type=MsgType.AudioOnlyClient, event=EventType.TaskRequest,
                               session_id=self.session_id, payload=data[i:i+chunk_size])
            await self.ws.send(msg.marshal())
            await asyncio.sleep(0.05) # Slightly faster
            
        # Send silence (Endpoint trigger)
        for _ in range(15):
             if self.completion_event.is_set(): break  # ⚡ Break if ASR done
             msg = DoubaoMessage(type=MsgType.AudioOnlyClient, event=EventType.TaskRequest,
                                session_id=self.session_id, payload=b'\x00'*3200)
             await self.ws.send(msg.marshal())
             await asyncio.sleep(0.1)
             
        try:
            await asyncio.wait_for(self.completion_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            print("❌ ASR Timeout", flush=True)
            return None

        print(f"🧠 Processing: {self.final_text}")
        t_start_agent = time.time()
        print(f"[PERF] 🚀 Agent Start: {t_start_agent:.3f}") # LOG 2
        
        # 🎯 Context-aware transitional phrases
        def get_transition_phrase(query: str) -> str:
            """Generate contextual transition phrase based on query intent"""
            import random
            
            # Intent-specific transitions
            if any(kw in query for kw in ["股价", "股票", "币价", "行情", "价格"]):
                return random.choice([
                    "好的，正在查询实时行情",
                    "稍等，马上为您查询股价",
                    "收到，正在连接行情服务器",
                    "让我看看最新的市场数据"
                ])
            
            elif any(kw in query for kw in ["天气", "温度", "下雨", "冷", "热"]):
                return random.choice([
                    "好的，正在查询天气情况",
                    "稍等，马上为您查询天气",
                    "让我看看天气预报",
                    "正在获取气象数据"
                ])
            
            elif any(kw in query for kw in ["播放", "音乐", "歌", "听"]):
                return random.choice([
                    "好的，正在为您准备音乐",
                    "马上为您播放",
                    "正在搜索歌曲",
                    "收到，正在连接音乐服务"
                ])
            
            elif any(kw in query for kw in ["搜索", "查一下", "找一下"]):
                return random.choice([
                    "好的，正在为您搜索",
                    "稍等，马上为您查询",
                    "正在搜索相关信息",
                    "让我帮您找找"
                ])
            
            elif any(kw in query for kw in ["计算", "乘", "加", "减", "除"]):
                return random.choice([
                    "好的，让我算一下",
                    "稍等，正在计算",
                    "马上为您计算结果"
                ])
            
            elif any(kw in query for kw in ["提醒", "日程", "安排"]):
                return random.choice([
                    "好的，正在为您设置提醒",
                    "收到，马上为您安排",
                    "正在添加到日程"
                ])
            
            elif any(kw in query for kw in ["新闻", "头条", "热点"]):
                return random.choice([
                    "好的，正在获取最新新闻",
                    "稍等，马上为您查询热点",
                    "正在连接新闻服务"
                ])
            
            # Generic fallback
            else:
                return random.choice([
                    "好的，让我想想",
                    "稍等，正在处理",
                    "收到，马上为您处理",
                    "好的，我来看看"
                ])
        
        # Detect if this needs a transition (tool queries)
        # Fix: Ensure self.final_text is not None before checking
        if not self.final_text:
             print("❌ Error: No text recognized")
             return None

        needs_transition = any(keyword in self.final_text for keyword in 
                              ["查询", "股价", "天气", "搜索", "计算", "提醒", "播放", "多少", "怎么样", "新闻"])
        
        if needs_transition:
            transition = get_transition_phrase(self.final_text)
            print(f"💬 [Transition]: {transition}")
            # ⚡ Play pre-cached audio instead of TTS (saves ~500ms)
            asyncio.create_task(play_cached_transition(transition))
            await asyncio.sleep(0.1)  # Minimal delay
        
        agent = get_agent()
        response = await agent.run(self.final_text)
        print(f"[PERF] ✅ Agent End: {time.time():.3f} (Duration: {(time.time()-t_start_agent)*1000:.0f}ms)") # LOG 3
        return response

    async def run_text(self, text):
        """Run pipeline with direct text input (Bypass ASR)"""
        print(f"🧠 Processing (Text Input): {text}")
        t_start_agent = time.time()
        print(f"[PERF] 🚀 Agent Start: {t_start_agent:.3f}")

        # Check for transitions
        await play_cached_transition(text)

        agent = get_agent()
        response = await agent.run(text)
        
        t_end_agent = time.time()
        print(f"[PERF] ✅ Agent End: {t_end_agent:.3f} (Duration: {(t_end_agent-t_start_agent)*1000:.0f}ms)")
        
        return response

# Transition text -> cache file mapping
TRANSITION_CACHE = {
    "好的，正在查询实时行情": "stock_1.wav",
    "稍等，马上为您查询股价": "stock_2.wav",
    "收到，正在连接行情服务器": "stock_3.wav",
    "让我看看最新的市场数据": "stock_4.wav",
    "好的，正在查询天气情况": "weather_1.wav",
    "稍等，马上为您查询天气": "weather_2.wav",
    "让我看看天气预报": "weather_3.wav",
    "正在获取气象数据": "weather_4.wav",
    "好的，正在为您准备音乐": "music_1.wav",
    "马上为您播放": "music_2.wav",
    "正在搜索歌曲": "music_3.wav",
    "收到，正在连接音乐服务": "music_4.wav",
    "好的，正在为您搜索": "search_1.wav",
    "稍等，马上为您查询": "search_2.wav",
    "正在搜索相关信息": "search_3.wav",
    "让我帮您找找": "search_4.wav",
    "好的，让我算一下": "calc_1.wav",
    "稍等，正在计算": "calc_2.wav",
    "马上为您计算结果": "calc_3.wav",
    "好的，正在为您设置提醒": "remind_1.wav",
    "收到，马上为您安排": "remind_2.wav",
    "正在添加到日程": "remind_3.wav",
    "好的，正在获取最新新闻": "news_1.wav",
    "稍等，马上为您查询热点": "news_2.wav",
    "正在连接新闻服务": "news_3.wav",
    "好的，让我想想": "generic_1.wav",
    "稍等，正在处理": "generic_2.wav",
    "收到，马上为您处理": "generic_3.wav",
    "好的，我来看看": "generic_4.wav",
}

CACHE_DIR = os.path.expanduser("~/Music/JarvisCache/transitions")

async def play_cached_transition(text: str):
    """Play pre-cached transition audio (instant, no TTS latency)"""
    t_start = time.time()
    
    filename = TRANSITION_CACHE.get(text)
    if not filename:
        print(f"  ⚠️ No cache for: {text}, falling back to TTS")
        await synthesize_and_play(text)
        return
    
    filepath = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  ⚠️ Cache file missing: {filepath}, falling back to TTS")
        await synthesize_and_play(text)
        return
    
    print(f"[PERF] ⚡ Cached Transition: {time.time():.3f} (Latency: {(time.time()-t_start)*1000:.0f}ms)")
    
    # Play with afplay (macOS) or mpg123 (Linux)
    import platform
    import subprocess
    if platform.system() == "Darwin":
        subprocess.Popen(["afplay", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["mpg123", "-q", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def synthesize_and_play(text):
    """Streaming TTS: Play audio chunks as they arrive (low latency)"""
    t_start_tts = time.time()
    print(f"[PERF] 🗣️ TTS Request: {t_start_tts:.3f}")
    
    # 🔥 Use global singleton for connection reuse
    tts = await get_tts()
    t_conn = time.time()
    await tts.connect()
    print(f"[PERF] 🔌 TTS Connected: {time.time():.3f} (Latency: {(time.time()-t_conn)*1000:.0f}ms)")
    
    # 🔥 Streaming playback: Open audio stream BEFORE receiving data
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,  # 16-bit
        channels=1,              # Mono
        rate=24000,              # TTS sample rate
        output=True,
        frames_per_buffer=1024
    )
    
    first_chunk = True
    chunk_count = 0
    
    try:
        async for chunk in tts.synthesize(text):
            if first_chunk:
                print(f"[PERF] 🎵 TTS First Byte: {time.time():.3f} (TTFB: {(time.time()-t_start_tts)*1000:.0f}ms)")
                print("🔊 Streaming playback...")
                first_chunk = False
            
            # ⚡ Play immediately as chunk arrives
            stream.write(chunk)
            chunk_count += 1
        
        print(f"✅ Playback complete ({chunk_count} chunks)")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    # 🔥 Don't close TTS - keep connection alive for reuse!
    # await tts.close()
    print(f"[PERF] 🏁 TTS Total: {(time.time()-t_start_tts)*1000:.0f}ms")

def record_audio(seconds=3):
    print("\n" + "="*60, flush=True)
    print("🎤 Voice Recorder", flush=True)
    print("="*60, flush=True)
    
    input("Press Enter to start recording...")
    print(f"🔴 Recording {seconds}s...", flush=True)
    
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    frames = []
    
    try:
        for i in range(0, int(16000 / 1024 * seconds)):
            data = stream.read(1024)
            frames.append(data)
            if i % 5 == 0: print(".", end="", flush=True)
    except KeyboardInterrupt:
        pass
        
    print("\n✅ Stopped")
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    with wave.open(INPUT_WAV, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b''.join(frames))
    print(f"Saved: {INPUT_WAV}")

if __name__ == "__main__":
    record_audio(seconds=4)
    
    demo = GoldenVoiceDemo()
    response = asyncio.run(demo.run_pipeline(INPUT_WAV))
    
    if response:
        asyncio.run(synthesize_and_play(response))
    
    print(f"\n{'='*60}")
    print("✅ DEMO COMPLETE")
    print(f"{'='*60}")
