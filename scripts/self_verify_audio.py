
import asyncio
import os
import sys
import json
import time
import wave
import threading
from datetime import datetime

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "jarvis_assistant"))

from jarvis_assistant.core.hybrid_jarvis import HybridJarvis

class VerifyingJarvis(HybridJarvis):
    def __init__(self, capture_file):
        self.capture_file = capture_file
        # Wave file setup (Stereo 48k for Mac compat)
        self.wav_file = wave.open(capture_file, 'wb')
        self.wav_file.setnchannels(2)
        self.wav_file.setsampwidth(2)
        self.wav_file.setframerate(48000)
        
        self.audio_received_event = asyncio.Event()
        self.total_bytes_captured = 0
        
        # Initialize resample states for parent class
        self.mic_resample_state = None
        self.ref_resample_state = None
        self.output_upsample_state = None
        
        super().__init__()

    def setup_audio(self):
        # Override to avoid physical device errors
        class MockStream:
            def write(self, data, *args, **kwargs): return len(data)
            def read(self, *args, **kwargs): return b'\x00' * 4800
            def stop_stream(self): pass
            def close(self): pass
            
        self.output_stream = MockStream()
        self.input_stream = MockStream()
        
        # Intercept write
        print("🛠️  Intercepting output_stream.write...")
        self._orig_write = self.output_stream.write
        self.output_stream.write = self._intercept_write
        
        # Speaker thread
        import queue
        import threading
        self.speaker_queue = queue.Queue(maxsize=100)
        self.speaker_thread = threading.Thread(target=self._speaker_worker, daemon=True)
        self.speaker_thread.start()

    def _intercept_write(self, data, *args, **kwargs):
        # Save to file
        if hasattr(self, 'wav_file') and self.wav_file:
            self.wav_file.writeframes(data)
        self.total_bytes_captured += len(data)
        if self.total_bytes_captured > 5000:
            self.audio_received_event.set()
        return self._orig_write(data, *args, **kwargs)

    async def run_verification(self):
        # 1. Start connecting in background
        connect_task = asyncio.create_task(self.connect())
        
        # 2. Wait for session to be established
        print("⏳ Waiting for session to be ready...")
        start_time = time.time()
        while not self.ws or not self.text_send_queue:
            await asyncio.sleep(0.5)
            if time.time() - start_time > 15:
                print("❌ Connection timeout")
                return False

        print("✅ Connection ready. Sending '你好'...")
        # 3. Send query
        await self.send_text_query("你好")
        
        # 4. Wait for audio
        print("⏳ Waiting for audio response...")
        try:
            # We wait for the audio_received_event to be set by _intercept_write
            await asyncio.wait_for(self.audio_received_event.wait(), timeout=20)
            print(f"✅ Audio flow detected! Total bytes captured: {self.total_bytes_captured}")
            
            # Wait for more chunks
            await asyncio.sleep(5)
            print(f"🏁 Final captured bytes: {self.total_bytes_captured}")
        except asyncio.TimeoutError:
            print("❌ Audio response timeout - no sound was output!")
            return False
        finally:
            self.is_running = False
            self.wav_file.close()
            try:
                if self.ws: await self.ws.close()
            except: pass
            
        return True

async def main():
    capture_path = os.path.join(project_root, "logs", "verification_output.wav")
    os.makedirs(os.path.dirname(capture_path), exist_ok=True)
    
    jarvis = VerifyingJarvis(capture_path)
    success = await jarvis.run_verification()
    
    if success:
        print(f"🎉 Verification file saved to: {capture_path}")
        print("🔍 Checking audio properties...")
        if os.path.getsize(capture_path) > 44: # WAV header size
            print("✅ Audio file is not empty.")
            # Now we should ideally transcribe it, but let's at least check size
        else:
            print("❌ Audio file is empty!")
    else:
        print("❌ Verification failed.")

if __name__ == "__main__":
    # Ensure we are in text-only mode for query send if needed, 
    # but we want real audio output for verification.
    os.environ["JARVIS_ALLOW_STDIN_PIPE"] = "1"
    asyncio.run(main())
