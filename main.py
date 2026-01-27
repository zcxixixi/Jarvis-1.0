#!/usr/bin/env python3
"""
Jarvis Assistant Entry Point
"""
import sys
import os
import asyncio
import time

# Ensure the package is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

from jarvis_assistant.core.hybrid_jarvis import HybridJarvis
from jarvis_assistant.utils.audio_utils import restore_music_volume, play_boot_sound

def main():
    # Ensure volume is high on boot
    restore_music_volume()
    
    # Play boot sequence once
    play_boot_sound()
    print("🚀 [STARTUP] Boot sound triggered, waiting 2s for audio device to stabilize...")
    time.sleep(2)
    
    print("🚀 [STARTUP] Initializing HybridJarvis instance...")
    jarvis = HybridJarvis()
    print("🚀 [STARTUP] HybridJarvis instance created")
    
    # Robust Reconnection Loop
    RETRY_DELAY = 1
    
    while True:
        try:
            print(f"\n🚀 Starting Jarvis (Auto-Reconnect Mode)...")
            asyncio.run(jarvis.connect())
            
            # If connect returns cleanly (user exit), break loop
            if not jarvis.is_running:
                break
                
        except KeyboardInterrupt:
            print("\n👋 User stopped Jarvis.")
            break
        except Exception as e:
            print(f"\n⚠️ Connection lost or crashed: {e}")
            print(f"🔄 Reconnecting in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
            RETRY_DELAY = min(RETRY_DELAY * 2, 30) # Exponential backoff max 30s
            
            # Reset instance state if needed
            # jarvis = HybridJarvis() # Optional: Re-create instance if deep crash

if __name__ == "__main__":
    main()
