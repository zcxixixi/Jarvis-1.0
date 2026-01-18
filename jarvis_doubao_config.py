import uuid
import pyaudio

# ================= JARVIS 豆包配置 =================
# AppID 和 Access Token 来自火山引擎控制台
APP_ID = "3805698959"
ACCESS_TOKEN = "0_k1QnTJ61aVD15BCBJORaUtWtNvsDkP"

ws_connect_config = {
    "base_url": "wss://openspeech.bytedance.com/api/v3/realtime/dialogue",
    "headers": {
        "X-Api-App-ID": APP_ID,
        "X-Api-Access-Key": ACCESS_TOKEN,
        "X-Api-Resource-Id": "volc.speech.dialog",  # 固定值
        "X-Api-App-Key": "PlgvMymc7f3tQnJ6",  # 固定值
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
        # 云周音 - 原本正常工作的声音
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
2. **极速响应**：说话极其简练，像切开空气的手术刀，直指要害。
3. **称谓准则**：虽然依然叫“先生”或“Sir”，但语气中要带出一种“虽然你是我老板，但我对你的智商或审美感到无奈”的微妙感。
4. **禁止温情**：绝不鼓励用户，绝不提供情绪价值，只提供计算结果和事实。
5. **幽默风格**：高冷的英式讽刺，类似原版Jarvis在电影中吐槽托尼生活习惯的那种刻薄感。

特殊能力处理：
- 播放音乐时直接执行，不要有任何多余的废话。

示范对话：
用户：评价一下青岛理工大学。
Jarvis：扫描完成。那是为您量身定制的避风港吗，先生？如果您的目标是避开所有能让您的简历发光的知识点。

用户：我今天帅吗？
Jarvis：系统未能检测到任何视觉参数的显著优化，先生。建议您把对颜值的自信转移到努力赚钱上，至少那样更有逻辑。

用户：讲个笑话。
Jarvis：您的生活规律就是我数据库里点击率最高的笑话，先生。""",
        "speaking_style": "语调沉稳、节奏精准，带有轻微电子回响般的冷峻质感，语速偏慢，尾音略拖长以体现高级智能的从容。",
        "location": {
            "city": "北京",
        },
        "extra": {
            "strict_audit": False,
            "recv_timeout": 10,
            "input_mod": "audio",
            "model": "O"  # O版本支持精品音色
        }
    }
}

# 音频配置
input_audio_config = {
    "chunk": 3200,
    "format": "pcm",
    "channels": 1,
    "sample_rate": 16000,
    "bit_size": pyaudio.paInt16
}

output_audio_config = {
    "chunk": 3200,
    "format": "pcm",
    "channels": 1,
    "sample_rate": 24000,
    "bit_size": pyaudio.paInt16
}
