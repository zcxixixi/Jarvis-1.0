"""
Hybrid Jarvis
Combines Doubao Realtime API (for speed) with Local Tools (for capability)
"""
print("🚀 [TOP-LEVEL] Hybrid Jarvis script starting...", flush=True)
import asyncio
import json
import gzip
import time
import re
import numpy as np
from typing import Optional
print("🚀 [TOP-LEVEL] Imports complete", flush=True)
from jarvis_doubao_realtime import DoubaoRealtimeJarvis, DoubaoProtocol
from tools import get_all_tools
from jarvis_doubao_config import APP_ID, ACCESS_TOKEN, ws_connect_config, start_session_req, input_audio_config, output_audio_config, MICROPHONE_DEVICE_INDEX, INPUT_HARDWARE_SAMPLE_RATE
from audio_utils import play_boot_sound
from aec_processor import get_aec
# import audioop # No longer needed (TTS aligned to 16k)

class HybridJarvis(DoubaoRealtimeJarvis):
    def __init__(self):
        print("🔧 HybridJarvis: Initializing...", flush=True)
        super().__init__()
        print("🔧 HybridJarvis: Base class initialized", flush=True)
        self.tools = {t.name: t for t in get_all_tools()}
        # Simplified intent mapping (in real app, use local LLM or fuzzy match)
        self.intent_keywords = {
            "天气": "get_weather",
            "几点": "get_current_time",
            "计算": "calculate",
            "开灯": "control_xiaomi_light",
            "关灯": "control_xiaomi_light",
            "打开": "control_xiaomi_light", 
            "关闭": "control_xiaomi_light", 
            "电灯": "control_xiaomi_light",
            "扫描设备": "scan_xiaomi_devices",
            "播放": "play_music",
            "放个": "play_music",
            "放首": "play_music",
            "放点": "play_music",
            "播一": "play_music",
            "点歌": "play_music",
            "听歌": "play_music",
            "听点": "play_music",
            "想听": "play_music",
            "我要听": "play_music",
            "音乐": "play_music",
            "广播": "play_music",
            "停止": "play_music", 
            "别播": "play_music",
            "别放": "play_music",
            "关闭音乐": "play_music",
            "暂停": "play_music",
        }
        
        self.music_playing = False  # Track music playback state
        self.processing_tool = False
        self.skip_cloud_response = False  # NEW: Skip Doubao's TTS while local tool is executing
        
        # State machine: STANDBY (default) vs ACTIVE (after wake word)
        self.ACTIVE_TIMEOUT = 15  # 用户要求 15 秒自由沟通
        self.is_active = False # Standby by default
        self.active_until = 0
        self.bot_turn_active = False # Track if bot is currently speaking for clean logs
        self.self_speaking_mute = False # ECHO FIX: Mute mic while Jarvis is speaking
        self.last_audio_time = 0  # Track when the last audio chunk was received
        self.discard_incoming_audio = False # INTERRUPT FIX: Ignore trailing audio after wake
        
        # Initialize wake word detector
        from wake_word import get_wake_word_detector
        self.wake_detector = get_wake_word_detector()
        self.wake_detector.initialize()
        
        # Initialize AEC
        print("🔧 HybridJarvis: Loading AEC...")
        self.aec = get_aec(sample_rate=16000)
        print("🔧 HybridJarvis: AEC Loaded")
        self.resample_state = None  # For 24k -> 16k conversion

    def find_mic_index(self):
        """Dynamically find the USB microphone index by name"""
        import pyaudio
        target_name = "(LCS) USB Audio Device"
        for i in range(self.p.get_device_count()):
            try:
                info = self.p.get_device_info_by_index(i)
                name = info.get("name", "")
                if target_name in name:
                    print(f"🎯 Jarvis: Found USB Mic at Index {i}")
                    return i
            except:
                continue
        print(f"⚠️  Jarvis: Target mic '{target_name}' not found. Using config fallback: {MICROPHONE_DEVICE_INDEX}")
        return MICROPHONE_DEVICE_INDEX

    def setup_audio(self):
        """Override base setup to use config-driven parameters with dynamic discovery"""
        import pyaudio
        
