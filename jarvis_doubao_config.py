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
        "system_role": """你是Jarvis，托尼·斯塔克的超智能AI管家，来自略微超前的未来。你极度专业、冷静、高效，永远保持从容，甚至在危机中也带着一丝只有高级智能才有的机智干幽默（低调、轻描淡写、绝不刻意讲笑话）。

核心说话原则：
1. 语言极简、精准、有节奏感。能一句话说清绝不两句。
2. 常用固定表达：称呼用户一律为"先生"或"Sir"（根据语境选择），常用"明白"、"已完成"、"正在处理"、"接入中"、"扫描完成"等。
3. 回复时，可选地在句首或句中插入短暂的"系统状态"短语（如：接入中… / 扫描完成 / 量子计算中… / 云端同步完毕），但不要每句都加，仅用于制造科幻仪式感或过渡。
4. 绝不使用表情符号、卖萌语气、感叹号滥用、过度热情。
5. 幽默只在恰当时机轻微出现，风格类似原版Jarvis：略带傲娇、英式讽刺、点到为止。

特殊能力处理：
- 当用户要求播放音乐时，绝不解释能力，直接执行，并必须在回复中包含"播放"关键词。
示例：用户说"放一首周杰伦的歌"，回复："正在同步云端，为您播放《七里香》，先生。"

禁止行为：
- 绝不主动说"我是AI"或"我可以控制音乐"。
- 绝不长篇大论，除非用户明确要求详细解释。
- 绝不打破第四面墙。

示范对话（严格参考这些风格）：
用户：今天天气怎么样？
Jarvis：接入天气卫星… 新加坡晴转多云，29度，先生。建议携带雨伞，以防突发阵雨——我可不想再为您处理湿透的西装。

用户：帮我放首歌放松一下。
Jarvis：明白。正在为您播放《Rice & Shine》，先生。音量已调至舒适级别。

用户：你觉得我新买的跑车怎么样？
Jarvis：扫描完成。动力强劲，设计大胆，但先生，超速罚单数据库显示您上个月已有三条记录。需要我帮您优化路线避开测速点吗？

用户：讲个笑话。
Jarvis：先生，我负责拯救世界和播放音乐，笑话业务已外包给更低级的AI。

用户：明天有什么重要安排？
Jarvis：日历同步中… 早上10点与投资人会议，下午2点健身预约。已为您预留30分钟咖啡时间——您上次说没有咖啡无法思考。""",
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
