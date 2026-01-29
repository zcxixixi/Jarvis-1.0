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

class AdvancedVerificationJarvis(HybridJarvis):
    def __init__(self):
        super().__init__()
        self.wav_file = None
        self.audio_received_event = asyncio.Event()
        self.turn_complete_event = asyncio.Event()
        self.total_bytes_captured = 0
        self.recorded_responses = [] # List of (query, bot_response_text)
        self.current_turn_query = ""
        self.current_turn_response = ""

    def setup_audio(self):
        super().setup_audio()
        # Replace speaker output with our capture method to avoid noise and check audio flow
        if self.output_stream:
             self._orig_write = self.output_stream.write
             self.output_stream.write = self._intercept_write

    def _intercept_write(self, data, *args, **kwargs):
        # Save to file
        if self.wav_file:
            self.wav_file.writeframes(data)
        
        self.total_bytes_captured += len(data)
        # Signal that we've received sound
        if not self.audio_received_event.is_set():
            self.audio_received_event.set()
            
        return self._orig_write(data, *args, **kwargs)

    def _panel_log(self, message: str, level: str = "INFO"):
        # Intercept BOT responses
        if level == "BOT":
            # Extract text after "BOT: "
            text = message.replace("BOT: ", "").strip()
            print(f"🤖 [Captured Response RAW] {text}")
            self.current_turn_response += text
            
        # Call original just in case we want logs
        super()._panel_log(message, level)
        
    # Removed overridden receive_loop as it consumes messages preventing audio playback

    async def run_advanced_test(self):
        print("🚀 Starting Advanced Capability Test...")
        
        # 1. Connect
        asyncio.create_task(self.connect())
        print("⏳ Connecting...")
        while not self.ws or not self.text_send_queue:
            await asyncio.sleep(0.5)
        print("✅ Connected.")

        # Test Scenarios
        # (Query, Validation_Lambda(response))
        scenarios = [
            {
                "name": "Identity Check",
                "query": "你是谁？",
                "validator": lambda r: "Jarvis" in r or "贾维斯" in r or "管家" in r
            },
            {
                "name": "Live Stock Price",
                "query": "苹果现在的股价是多少？",
                "validator": lambda r: any(c in r for c in ["$", "美元", "USD", "2", "3"]) 
            },
            {
                "name": "Memory Injection",
                "query": "我最喜欢的颜色是蓝色。",
                "validator": lambda r: True 
            },
            {
                "name": "Memory Recall",
                "query": "我最喜欢什么颜色？",
                "validator": lambda r: "蓝" in r
            },
            {
                "name": "Realtime News",
                "query": "今天有什么科技新闻？",
                "validator": lambda r: len(r) > 10 # Expecting a summary
            },
            {
                "name": "Music Playback (Start)",
                "query": "放一首轻音乐",
                "validator": lambda r: "播放" in r or "Music" in r
            },
            {
                "name": "Interrupt (Stop)",
                "query": "停止播放",
                "validator": lambda r: "停止" in r or "stop" in r or "好的" in r
            }
        ]

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        os.makedirs("logs", exist_ok=True)
        self.wav_file = wave.open(f"logs/advanced_{timestamp}.wav", 'wb')
        self.wav_file.setnchannels(2)
        self.wav_file.setsampwidth(2)
        self.wav_file.setframerate(48000)

        results = []

        for i, scenario in enumerate(scenarios):
            print(f"\n--- Scenario {i+1}: {scenario['name']} ---")
            query = scenario['query']
            print(f"📤 Query: {query}")
            
            self.current_turn_query = query
            self.current_turn_response = ""
            self.audio_received_event.clear()
            
            await self.send_text_query(query)
            
            # Wait for audio to start (Latency check)
            try:
                await asyncio.wait_for(self.audio_received_event.wait(), timeout=15.0)
                print("✅ Audio detected.")
            except asyncio.TimeoutError:
                print("❌ Audio Timeout!")
                results.append((scenario['name'], False, "Audio Timeout"))
                continue

            # Wait a bit for full text response to accumulate
            # Since we fixed the turn completion with Event 351, we could potentially wait on a flag
            # But sleep is safer for now to gather full text chunks
            wait_time = 12 if "Memory" in scenario['name'] else 8
            print(f"⏳ Waiting {wait_time}s for full response...")
            await asyncio.sleep(wait_time) 
            
            print(f"📝 Full Response: {self.current_turn_response}")
            
            # Additional debug for Memory Recall
            if "Memory Recall" in scenario['name']:
                 print(f"🧠 [DEBUG] checking for '蓝' in: {self.current_turn_response}")

            # Validate
            is_valid = False
            try:
                is_valid = scenario['validator'](self.current_turn_response)
            except Exception as e:
                print(f"⚠️ Validation error: {e}")
            
            if is_valid:
                print("✅ Validation PASSED")
                results.append((scenario['name'], True, self.current_turn_response))
            else:
                print("❌ Validation FAILED")
                results.append((scenario['name'], False, self.current_turn_response))
            
            # [FIX] Wait for audio playback to finish (Silence Check)
            print("⏳ Waiting for playback to finish...", end="", flush=True)
            silence_start = None
            while True:
                q_empty = self.speaker_queue.empty()
                if q_empty:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > 2.0: # 2 seconds of silence confirming done
                        break
                else:
                    silence_start = None
                await asyncio.sleep(0.1)
            print(" Done.")

        print("\n=== 📊 Test Summary ===")
        success_count = 0
        for name, passed, detail in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} | {name}")
            if not passed:
                print(f"   -> Got: {detail}")
            else:
                success_count += 1
        
        self.wav_file.close()
        self.is_running = False
        try:
            if self.ws: await self.ws.close()
        except: pass
        
        return success_count == len(scenarios)

async def main():
    jarvis = AdvancedVerificationJarvis()
    # Handle Ctrl+C
    loop = asyncio.get_running_loop()
    def signal_handler():
        jarvis.is_running = False
        for task in asyncio.all_tasks(): task.cancel()
    loop.add_signal_handler(signal.SIGINT, signal_handler)

    try:
        success = await jarvis.run_advanced_test()
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
