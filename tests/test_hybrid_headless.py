"""
Headless connection test for Hybrid Jarvis
Verifies connection and handshake without audio hardware
"""
import asyncio
import sys
import time
# Mock pyaudio before importing jarvis modules
from unittest.mock import MagicMock
sys.modules['pyaudio'] = MagicMock()

from hybrid_jarvis import HybridJarvis

async def test_connection():
    print("🧪 Starting Hybrid Jarvis Headless Test...")
    
    # Instantiate
    jarvis = HybridJarvis()
    
    # Mock audio methods to avoid PyAudio calls
    jarvis.setup_audio = MagicMock()
    jarvis.send_audio_loop = MagicMock(return_value=asyncio.Future())
    jarvis.send_audio_loop.return_value.set_result(None) # Immediate return or sleep
    
    # Override receive_loop to just wait for handshake
    original_receive = jarvis.receive_loop
    
    async def fast_receive():
        try:
            print("🎧 Waiting for initial responses...")
            # We just want to see if connect() succeeds without error
            # connect() itself handles start_connection and start_session
            # If we get here, those passed with "await ws.recv()"
            print("✅ Handshake successful! Connection established.")
            
            # Keep alive briefly
            await asyncio.sleep(2)
            
            # Stop
            jarvis.is_running = False
            if jarvis.ws:
                await jarvis.ws.close()
                
        except Exception as e:
            print(f"❌ Receive loop error: {e}")

    jarvis.receive_loop = fast_receive
    
    # Run connect
    try:
        await jarvis.connect()
        print("✅ Test Completed Successfully")
    except Exception as e:
        print(f"❌ Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
