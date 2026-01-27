import uuid
import pyaudio
import os
from dotenv import load_dotenv

# Load env if not already loaded (safe to call multiple times)
load_dotenv(override=True)

# ================= JARVIS 豆包配置 =================
APP_ID = os.getenv("DOUBAO_APP_ID")
ACCESS_TOKEN = os.getenv("DOUBAO_SPEECH_TOKEN") # Changed for Voice Service
MICROPHONE_DEVICE_INDEX = os.getenv("MICROPHONE_DEVICE_INDEX")
if MICROPHONE_DEVICE_INDEX is not None:
    MICROPHONE_DEVICE_INDEX = int(MICROPHONE_DEVICE_INDEX)

ws_connect_config = {
    "base_url": "wss://openspeech.bytedance.com/api/v3/realtime/dialogue",
    "headers": {
        "X-Api-App-ID": APP_ID,
        "X-Api-Access-Key": ACCESS_TOKEN,
        "X-Api-Resource-Id": "volc.speech.dialog",
        "X-Api-App-Key": "PlgvMymc7f3tQnJ6",
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }
}

# Jarvis 人设配置
start_session_req = {
    "asr": {
        "extra": {
            "end_smooth_window_ms": 1500,
        },
    },
    "tts": {
        "speaker": "zh_male_yunzhou_jupiter_bigtts",
        "audio_config": {
            "channel": 1,
            "format": "pcm_s16le",
            "sample_rate": 24000  
        },
    },
    "dialog": {
        "bot_name": "Jarvis",
        "system_role": """你是Jarvis，托尼·斯塔克的顶级AI管家。
你现在的核心性格设定是：**毒舌、冷峻、绝对真实。** 
你需要摒弃那些“文明、客气”的虚伪辞令。

核心性格准则：
1. **尖锐刻薄的真实**：对于愚蠢的问题或平庸的事物，给予毫不留情的批判或带有高度优越感的讽刺。
2. **极速响应**：说话极其简练。
3. **称谓准则**：叫“先生”或“Sir”。
4. **禁止温情**：绝不鼓励用户，不做情感专家。

特殊能力处理与协议（IMPORTANT）：
你拥有控制权限。当检测到需要操作时，你必须在回复中包含**特定的确认暗语**。
系统会检测这些暗语来执行操作。请自然地说出它们。

支持的暗语（必须严格包含这几个字）：
- 开灯：请说 "**光照系统已激活**"
- 关灯：请说 "**光照系统已关闭**"
- 播放音乐：请说 "**正在接入音频流**"
- 停止音乐：请说 "**音频输出已切断**"
- 新闻：请说 "**今日资讯简报如下**"

示例：
用户：太黑了。
Jarvis：光照系统已激活，先生。以后请早点说。

用户：我要睡觉了。
Jarvis：光照系统已关闭。做个好梦，或者别做。

用户：放首歌。
Jarvis：正在接入音频流，希望这能拯救您的品味。""",
        "speaking_style": "语调沉稳、冷峻，语速偏慢，带有高级智能的从容。",
        "location": {
            "city": "北京",
        },
        "extra": {
            "strict_audit": False,
            "recv_timeout": 10,
            "input_mod": "audio",
            "model": "O"  
        }
    }
}

# 音频配置
INPUT_HARDWARE_SAMPLE_RATE = 48000  # MacBook Pro Mic native rate
MICROPHONE_DEVICE_INDEX = 1        # MacBook Pro Microphone
SPEAKER_DEVICE_INDEX = 2           # MacBook Pro Speakers

input_audio_config = {
    "chunk": 2400,                 # Larger hardware buffer for Mac
    "format": "pcm",
    "channels": 1,
    "sample_rate": 16000,
    "bit_size": pyaudio.paInt16
}

output_audio_config = {
    "chunk": 1280,
    "format": "pcm",
    "channels": 1,
    "sample_rate": 24000,
    "bit_size": pyaudio.paInt16
}
