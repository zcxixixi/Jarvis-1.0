"""
Configuration Module
All settings in one place
"""

from dataclasses import dataclass, field
from typing import Optional, List
import os

@dataclass
class AudioConfig:
    """Audio I/O configuration"""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 480  # 30ms at 16kHz
    speaker_channels: int = 2  # Stereo output
    device_name: Optional[str] = None

@dataclass
class VADConfig:
    """Voice Activity Detection configuration"""
    threshold: float = 0.5
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 500
    sample_rate: int = 16000

@dataclass
class WakeWordConfig:
    """Wake word detection configuration"""
    models: List[str] = field(default_factory=lambda: ["hey_jarvis_v0.1"])
    threshold: float = 0.5
    debounce_seconds: float = 2.0

@dataclass
class ASRConfig:
    """Automatic Speech Recognition configuration"""
    provider: str = "doubao"
    language: str = "zh-CN"
    app_id: str = field(default_factory=lambda: os.getenv("DOUBAO_APP_ID", ""))
    access_token: str = field(default_factory=lambda: os.getenv("DOUBAO_ACCESS_TOKEN", ""))

@dataclass
class TTSConfig:
    """Text-to-Speech configuration"""
    provider: str = "doubao"
    voice: str = "zh_female_shuangkuaisisi_moon_bigtts"
    app_id: str = field(default_factory=lambda: os.getenv("DOUBAO_APP_ID", ""))
    access_token: str = field(default_factory=lambda: os.getenv("DOUBAO_ACCESS_TOKEN", ""))
    pool_size: int = 1  # Connection pooling

@dataclass
class AgentConfig:
    """Agent configuration"""
    model: str = "doubao-pro-32k"
    temperature: float = 0.7
    max_tokens: int = 150
    timeout: int = 30

@dataclass
class JarvisConfig:
    """Master configuration"""
    audio: AudioConfig = field(default_factory=AudioConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    
    # User context
    user_location: str = "菏泽, 山东"
    user_name: str = "User"
    
    # System
    log_level: str = "INFO"
    enable_boot_sound: bool = True

# Global config instance
config = JarvisConfig()

def load_config(config_file: str = None):
    """Load configuration from file"""
    if config_file and os.path.exists(config_file):
        import json
        with open(config_file) as f:
            data = json.load(f)
            # Update config
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    return config
