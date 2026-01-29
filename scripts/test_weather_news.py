
import asyncio
import os
import sys
import json
import time

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "jarvis_assistant"))

from jarvis_assistant.core.hybrid_jarvis import HybridJarvis

class ToolTesterJarvis(HybridJarvis):
    def __init__(self):
        self.results = []
        self.audio_received = asyncio.Event()
        super().__init__()

    def setup_audio(self):
        # Mocking audio hardware
        class MockStream:
            def write(self, *args, **kwargs): return len(args[0])
            def stop_stream(self): pass
            def close(self): pass
            def read(self, *args, **kwargs): return b'\x00' * 4800
        self.output_stream = MockStream()
        self.input_stream = MockStream()
        
        # Override speaker worker to signal audio reception
        import queue
        import threading
        self.speaker_queue = queue.Queue(maxsize=100)
        self.speaker_thread = threading.Thread(target=self._test_speaker_worker, daemon=True)
        self.speaker_thread.start()

    def _test_speaker_worker(self):
        while self.is_running:
            try:
                # Use a smaller timeout and check for Empty
                try:
                    data = self.speaker_queue.get(timeout=0.1)
                    if data:
                        loop = asyncio.get_event_loop()
                        loop.call_soon_threadsafe(self.audio_received.set)
                        # [FIX] Simulate real-time playback consumption to avoid QueueFull
                        # 24k samples/s, 16-bit, 2 channels = 96000 bytes/s
                        time.sleep(len(data) / 96000.0) 
                    self.speaker_queue.task_done()
                except queue.Empty:
                    continue
            except: continue

    async def run_test(self, label, query):
        print(f"\n--- Testing Tool: {label} ({query}) ---")
        self.audio_received.clear()
        start_time = time.time()
        
        await self.send_text_query(query)
        
        try:
            # Wait for audio chunks to start flowing
            await asyncio.wait_for(self.audio_received.wait(), timeout=20)
            latency = (time.time() - start_time) * 1000
            print(f"✅ {label} Success. Response started in {latency:.1f}ms")
            
            # Briefly wait to capture a few more chunks/logs
            await asyncio.sleep(4)
        except asyncio.TimeoutError:
            print(f"❌ {label} Failed: No audio response received within timeout.")

async def main():
    tester = ToolTesterJarvis()
    print("🚀 Initializing Jarvis Tool Tester...")
    
    # 1. Connect
    connect_task = asyncio.create_task(tester.connect())
    start_wait = time.time()
    while not tester.ws or not tester.text_send_queue:
        await asyncio.sleep(0.5)
        if time.time() - start_wait > 15:
            print("❌ Connection timeout")
            return

    # 2. Test Weather
    await tester.run_test("Weather", "北京天气怎么样")
    
    # 3. Test News
    await tester.run_test("News", "播报一下今天的科技新闻")

    print("\n🏁 Tool tests completed.")
    tester.is_running = False
    if tester.ws: await tester.ws.close()

if __name__ == "__main__":
    os.environ["JARVIS_ALLOW_STDIN_PIPE"] = "1"
    asyncio.run(main())
