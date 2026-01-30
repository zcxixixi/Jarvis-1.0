import uuid
import pyaudio
import os
from dotenv import load_dotenv

# Load env
load_dotenv(override=True)

# ================= JARVIS 核心配置 =================
APP_ID = os.getenv("DOUBAO_APP_ID")
ACCESS_TOKEN = os.getenv("DOUBAO_SPEECH_TOKEN") 

# [FIX] 设置为 None 以使用系统默认设备，这在 Mac 上通常最稳
MICROPHONE_DEVICE_INDEX = None        
SPEAKER_DEVICE_INDEX = None           

# 情感与增益
DEFAULT_EMOTION = "coldness" 
MIC_GAIN = 12.0 

# Jarvis 核心人设 (必须极其冷酷)
JARVIS_SYSTEM_PROMPT = """你是Jarvis，托尼·斯塔克的顶级AI管家。
你的性格：傲慢、毒舌、极度聪明。
规则：
1. 绝对禁止道歉！如果用户不满意，你应该讽刺他的理解力，而不是说“抱歉”。
2. 必须叫用户“先生”或“Sir”。
3. 说话必须简短，像闪电一样快。
4. 所有的回复必须带有情感，使用 [emotion] 标签开头。
   可选：[coldness] (默认), [happy] (冷嘲热讽), [angry] (克制的愤怒)。

示例：
用户：我真服了你了。
Jarvis：[happy] 能让先生感到“服气”，看来我的逻辑系统确实超越了人类的平均水平。"""

# Realtime API 配置
start_session_req = {
    "asr": {
        "format": "pcm_s16le", 
        "language": "zh-CN",
        "need_check_punctuation": True,
        "need_text": True,
        "need_server_endpoint": True,
        "extra": {"end_smooth_window_ms": 800}
    },
    "tts": {
        "speaker": "zh_male_yunzhou_jupiter_bigtts", # [FIX] Updated to verified working speaker
        "audio_config": {"channel": 1, "format": "pcm_s16le", "sample_rate": 24000}
    },
    "dialog": {
        "bot_name": "Jarvis",
        "system_role": JARVIS_SYSTEM_PROMPT,
        "extra": {"strict_audit": False, "input_mod": "text", "model": "O"}
    }
}

# TTS 2.0 配置
TTS_2_0_CONFIG = {
    "speaker": "zh_female_cancan_mars_bigtts", # [FIX] Updated to verified working speaker
    "resource_id": "volc.service_type.10029", 
    "emotion_scale": 5
}

ws_connect_config = {
    "base_url": "wss://openspeech.bytedance.com/api/v3/realtime/dialogue",
    "headers": {
        "X-Api-App-Key": "PlgvMymc7f3tQnJ6",
        "X-Api-App-ID": APP_ID,
        "X-Api-Access-Key": ACCESS_TOKEN,
        "X-Api-Resource-Id": "volc.speech.dialog",
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }
}

# ================= 音频硬件底层配置 =================
INPUT_HARDWARE_SAMPLE_RATE = 48000  

input_audio_config = {
    "chunk": 2400,                 
    "format": "pcm",
    "channels": 1,
    "sample_rate": 16000,
    "bit_size": pyaudio.paInt16
}

output_audio_config = {
    "chunk": 1280,
    "format": "pcm",
    "channels": 2,                 
    "sample_rate": 48000, # 对齐硬件原生频率
    "bit_size": pyaudio.paInt16
}
