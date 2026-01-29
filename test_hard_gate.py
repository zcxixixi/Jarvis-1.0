import queue
import time
import threading
import sys

# Mock HybridJarvis class
class MockJarvis:
    def __init__(self):
        self.speaker_queue = queue.Queue()
        self.is_running = True
        self.skip_cloud_response = False # The flag driving the gate
        self.dropped_count = 0
        self.played_count = 0
        
    def _speaker_worker(self):
        print("🧵 [MOCK] Worker started.")
        while self.is_running:
            try:
                data = self.speaker_queue.get(timeout=0.1)
                
                # --- LOGIC COPIED FROM HYBRIDJARVIS.PY ---
                # Unpack tag if present (tag, data)
                tag = "unknown"
                if isinstance(data, tuple):
                    tag, data = data
                
                # If it's S2S audio and we are suppressing Cloud (Agent Path active), DROP IT
                if tag == "s2s" and getattr(self, "skip_cloud_response", False):
                     print(f"🔇 [GATE] Dropped S2S packet (Tag: {tag})")
                     self.dropped_count += 1
                     self.speaker_queue.task_done()
                     continue
                # -----------------------------------------

                print(f"🔊 [PLAY] Playing packet (Tag: {tag})")
                self.played_count += 1
                self.speaker_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error: {e}")

# Test Scenario
def run_test():
    jarvis = MockJarvis()
    worker = threading.Thread(target=jarvis._speaker_worker, daemon=True)
    worker.start()

    print("\n--- TEST 1: Normal Mode (Flag=False) ---")
    jarvis.skip_cloud_response = False
    jarvis.speaker_queue.put(("s2s", b"audio_s2s_1"))
    jarvis.speaker_queue.put(("agent", b"audio_agent_1"))
    time.sleep(0.5)
    
    print("\n--- TEST 2: Suppression Mode (Flag=True) ---")
    jarvis.skip_cloud_response = True
    jarvis.speaker_queue.put(("s2s", b"audio_s2s_2_SHOULD_DROP"))
    jarvis.speaker_queue.put(("agent", b"audio_agent_2_SHOULD_PLAY"))
    time.sleep(0.5)

    print("\n--- TEST 3: Edge Case (Untagged) ---")
    jarvis.speaker_queue.put(b"untagged_audio")
    time.sleep(0.5)

    jarvis.is_running = False
    time.sleep(0.1)

    print("\n--- RESULTS ---")
    print(f"Total Played: {jarvis.played_count} (Expected: 4)") # s2s_1, agent_1, agent_2, untagged
    print(f"Total Dropped: {jarvis.dropped_count} (Expected: 1)") # s2s_2
    
    if jarvis.dropped_count == 1 and jarvis.played_count == 4:
        print("✅ LOGIC VERIFIED: Correct")
    else:
        print("❌ LOGIC FAILED")

if __name__ == "__main__":
    run_test()
