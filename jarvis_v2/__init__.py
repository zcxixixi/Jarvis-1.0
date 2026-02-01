# Jarvis V2 - Modular Voice AI Assistant
# Complete restructuring using open-source components

__version__ = "2.0.0"
__author__ = "Jarvis Team"

# Re-export main components for easy import
from .session.session import JarvisSession
from .components.audio_io import AudioIO
from .agent.jarvis_agent import JarvisAgent

__all__ = [
    "JarvisSession",
    "AudioIO", 
    "JarvisAgent",
]
