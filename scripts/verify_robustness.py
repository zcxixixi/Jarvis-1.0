import asyncio
import sys
import os
import signal
import time
import wave
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis_assistant.core.hybrid_jarvis import HybridJarvis

class VerificationJarvis(HybridJarvis):
    def __init__(self):
        super().__init__()
        self.wav_file = None
        self.audio_received_event = asyncio.Event()
        self.turn_complete_event = asyncio.Event()
        self.total_bytes_captured = 0
        self.dialog_ids = []
        self.latencies = []
        self.current_turn_start = 0

    def setup_audio(self):
        super().setup_audio()
        # Replace speaker output with our capture method
        if self.output_stream:
             print("🛠️ Intercepting output_stream.write...")
             self._orig_write = self.output_stream.write
             self.output_stream.write = self._intercept_write

    def _intercept_write(self, data, *args, **kwargs):
        # Calculate latency for the first chunk of a turn
        if self.current_turn_start > 0:
            latency = time.time() - self.current_turn_start
            print(f"⏱️  Latency: {latency*1000:.2f}ms")
            self.latencies.append(latency)
            self.current_turn_start = 0 # Reset for this turn

        # Save to file
        if self.wav_file:
            self.wav_file.writeframes(data)
        
        self.total_bytes_captured += len(data)
        # Signal that we've received sound
        if not self.audio_received_event.is_set():
            self.audio_received_event.set()
            
        return self._orig_write(data, *args, **kwargs)
    
    # Override receive_loop to catch turn ends (if needed) or just rely on silence
    # For verification, we loop based on events

    async def run_robustness_test(self):
        print("🚀 Starting Robustness Test (3 Turns)...")
        
        # 1. Connect
        connect_task = asyncio.create_task(self.connect())
        print("⏳ Waiting for session...")
        wait_start = time.time()
        while not self.ws or not self.text_send_queue:
            await asyncio.sleep(0.5)
            if time.time() - wait_start > 15:
                print("❌ Connection Timeout")
                return False
        print("✅ Connection Ready.")

        queries = [
            "你好", 
            "你叫什么名字", 
            "今天天气怎么样"
        ]

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        filename = f"{log_dir}/robustness_{timestamp}.wav"
        
        self.wav_file = wave.open(filename, 'wb')
        self.wav_file.setnchannels(2) # Stereo from config
        self.wav_file.setsampwidth(2) # 16-bit
        self.wav_file.setframerate(48000)

        for i, query in enumerate(queries):
            print(f"\n--- Turn {i+1}: '{query}' ---")
            self.audio_received_event.clear()
            self.current_turn_start = time.time()
            
            await self.send_text_query(query)
            
            # Wait for audio start
            try:
                await asyncio.wait_for(self.audio_received_event.wait(), timeout=10)
                print(f"✅ Audio started for Turn {i+1}")
            except asyncio.TimeoutError:
                print(f"❌ Turn {i+1} Timeout - No Audio!")
                return False

            # Capture Context
            if hasattr(self, 'dialog_id'):
                print(f"🆔 Dialog ID: {self.dialog_id}")
                self.dialog_ids.append(self.dialog_id)
            
            # Wait for 'completion' (simulate listening to full answer)
            # In a real app we'd wait for TTSSentenceEnd, but here we just wait for valid audio flow
            await asyncio.sleep(5) 

        print("\n=== Test Results ===")
        print(f"✅ Completed {len(queries)} turns.")
        print(f"⏱️  Average Latency: {sum(self.latencies)/len(self.latencies)*1000:.2f}ms" if self.latencies else "Latency: N/A")
        print(f"🆔 Dialog IDs: {self.dialog_ids}")
        
        if len(set(self.dialog_ids)) <= 1:
             print("✅ Context Preserved (Dialog ID stable/consistent).")
        else:
             print("⚠️  Dialog ID changed (Context reset?).")

        self.is_running = False
        self.wav_file.close()
        try:
            if self.ws: await self.ws.close()
        except: pass
        return True

async def main():
    jarvis = VerificationJarvis()
    
    # Handle Ctrl+C
    loop = asyncio.get_running_loop()
    def signal_handler():
        print("\n🛑 Interrupt received, shutting down...")
        jarvis.is_running = False
        # Cancel all tasks
        for task in asyncio.all_tasks():
            task.cancel()
            
    loop.add_signal_handler(signal.SIGINT, signal_handler)

    try:
        success = await jarvis.run_robustness_test()
        sys.exit(0 if success else 1)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
