"""
JARVIS Configuration Module
Manages all configuration settings
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """JARVIS Configuration"""
    
    # LLM Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower() # groq, grok, or ollama
    
    # Groq API Settings (Free, Ultra Fast!)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Grok API Settings
    GROK_API_KEY = os.getenv("GROK_API_KEY", "")
    GROK_API_BASE = os.getenv("GROK_API_BASE", "https://api.x.ai/v1")
    GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.1-fast")
    
    # Ollama Settings
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    
    # Voice Settings
    ENABLE_VOICE = os.getenv("ENABLE_VOICE", "false").lower() == "true"
    USE_GROK_VOICE = os.getenv("USE_GROK_VOICE", "false").lower() == "true"
    TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")
    
    # Hardware Settings
    BLUETOOTH_SPEAKER_MAC = os.getenv("BLUETOOTH_SPEAKER_MAC", "")
    MICROPHONE_DEVICE_INDEX = int(os.getenv("MICROPHONE_DEVICE_INDEX", "0"))
    
    # Smart Home
    HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL", "")
    HOME_ASSISTANT_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN", "")
    
    # Debug
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # JARVIS Personality
    SYSTEM_PROMPT = """你是贾维斯（JARVIS），一个高级AI助手。

你的特点：
- 专业、礼貌、高效
- 提供简洁明确的回答
- 主动提供建议和帮助
- 像真正的私人助理一样服务用户

你可以帮助用户：
- 回答问题和提供信息
- 执行各种任务和查询
- 控制智能家居设备（未来功能）
- 管理日程和提醒

请用中文回复，保持专业友好的语气。"""

    # Conversation Settings
    MAX_CONTEXT_MESSAGES = 10  # 保留最近10条对话
    TEMPERATURE = 0.7
    MAX_TOKENS = 1000
    
    @classmethod
    def validate(cls):
        """验证配置"""
        if cls.LLM_PROVIDER == "grok":
            if not cls.GROK_API_KEY:
                raise ValueError("使用 Grok 模式时，请在 .env 文件中设置 GROK_API_KEY")
        return True

# Validate on import
if __name__ != "__main__":
    Config.validate()
