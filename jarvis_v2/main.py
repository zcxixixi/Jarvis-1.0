#!/usr/bin/env python3
"""
Jarvis V2 - Main Entry Point
Total: ~50 lines (vs 2682 before!)
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jarvis_v2.session.session import JarvisSession
from jarvis_v2.config import JarvisConfig

async def main():
    """Main entry point"""
    
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║                 JARVIS V2.0                          ║
    ║          Modular Voice AI Assistant                 ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    # Load configuration
    config = JarvisConfig()
    
    print(f"📍 User Location: {config.user_location}")
    print(f"👤 User Name: {config.user_name}")
    print(f"🎤 Wake Word Models: {config.wake_word.models}")
    print(f"🗣️ TTS Voice: {config.tts.voice}")
    
    # Create session
    session = JarvisSession(config)
    
    # Run
    try:
        await session.start()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
