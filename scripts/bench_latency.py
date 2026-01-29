
import asyncio
import os
import sys
import json
import time
import wave
from datetime import datetime

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "jarvis_assistant"))

from jarvis_assistant.core.hybrid_jarvis import HybridJarvis

class LatencyBenchJarvis(HybridJarvis):
    def __init__(self):
        self.latency_metrics = []
        self._current_start_time = 0
        self._first_audio_chunk_time = 0
        self.audio_event = asyncio.Event()
        super().__init__()

    def setup_audio(self):
        # Mocking audio hardware to avoid needing physical device for pure latency test
        class MockStream:
            def write(self, *args, **kwargs): return len(args[0])
            def stop_stream(self): pass
            def close(self): pass
            def read(self, *args, **kwargs): return b'\x00' * 4800
        self.output_stream = MockStream()
        self.input_stream = MockStream()
        
        # Override speaker worker to measure latency
        import queue
        import threading
        self.speaker_queue = queue.Queue(maxsize=100)
        self.speaker_thread = threading.Thread(target=self._latency_speaker_worker, daemon=True)
        self.speaker_thread.start()
        
        # [FIX] Initialize resample states to avoid VerifyingJarvis-like errors
        self.mic_resample_state = None
        self.ref_resample_state = None
        self.output_upsample_state = None

    def _latency_speaker_worker(self):
        while self.is_running:
            try:
                data = self.speaker_queue.get(timeout=1.0)
                if data is None: continue
                if self._first_audio_chunk_time == 0:
                    self._first_audio_chunk_time = time.time()
                    loop = asyncio.get_event_loop()
                    loop.call_soon_threadsafe(self.audio_event.set)
                self.speaker_queue.task_done()
            except: continue

    async def measure_query(self, label, text):
        print(f"--- Benchmarking: {label} ---")
        self.audio_event.clear()
        self._first_audio_chunk_time = 0
        self._current_start_time = time.time()
        
        await self.send_text_query(text)
        
        try:
            await asyncio.wait_for(self.audio_event.wait(), timeout=15)
            latency = (self._first_audio_chunk_time - self._current_start_time) * 1000
            print(f"✅ Response received. First Byte Latency: {latency:.1f}ms")
            self.latency_metrics.append({"label": label, "latency_ms": latency})
        except asyncio.TimeoutError:
            print(f"❌ Timed out waiting for: {label}")
            self.latency_metrics.append({"label": label, "latency_ms": None})

async def main():
    bench = LatencyBenchJarvis()
    print("🚀 Starting Latency Benchmark...")
    
    # 1. Connect
    connect_task = asyncio.create_task(bench.connect())
    start_wait = time.time()
    while not bench.ws or not bench.text_send_queue:
        await asyncio.sleep(0.5)
        if time.time() - start_wait > 15:
            print("❌ Connection timeout")
            return

    # 2. Test Scenarios
    # Scenario A: Simple Greeting (Jupiter Fast Path)
    await bench.measure_query("Fast Path: Greeting", "你好")
    await asyncio.sleep(3) # Wait for finish
    
    # Scenario B: Tool Trigger (Agent Planning Path)
    await bench.measure_query("Slow Path: Stock Query", "查询英伟达股价")
    await asyncio.sleep(5)
    
    # Scenario C: Long Context (Conversation History)
    await bench.measure_query("Contextual: Follow-up", "它今天涨了吗？")
    await asyncio.sleep(5)

    # 3. Report
    print("\n" + "="*30)
    print("📊 LATENCY REPORT")
    print("="*30)
    for m in bench.latency_metrics:
        val = f"{m['latency_ms']:.1f}ms" if m['latency_ms'] else "TIMEOUT"
        print(f"{m['label']:<20}: {val}")
    print("="*30)

    bench.is_running = False
    if bench.ws: await bench.ws.close()

if __name__ == "__main__":
    asyncio.run(main())
