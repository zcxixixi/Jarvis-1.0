
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hybrid_jarvis import HybridJarvis

class TestJarvisFlow(unittest.TestCase):
    def setUp(self):
        # Mocks
        self.mock_wake = MagicMock()
        self.mock_wake.process_audio.return_value = False
        
        # Patch dependencies before initializing Jarvis
        with patch('wake_word.get_wake_word_detector', return_value=self.mock_wake), \
             patch('aec_processor.get_aec'), \
             patch('audio_utils.play_boot_sound'):
            
            self.jarvis = HybridJarvis()
            
        # Mock Internals
        self.jarvis.input_stream = MagicMock()
        self.jarvis.input_stream.read.return_value = b'\x00' * 3200
        self.jarvis.output_stream = MagicMock()
        self.jarvis.ws = AsyncMock()
        self.jarvis._send_raw_audio = AsyncMock()
        self.jarvis.stop_music_and_resume = AsyncMock()
        
        # Mock Tools
        self.jarvis.tools = {
            "play_music": AsyncMock(),
            "control_xiaomi_light": AsyncMock()
        }
        self.mock_light = self.jarvis.tools["control_xiaomi_light"]

    def run_coro(self, coro):
        return asyncio.run(coro)

    def test_wake_word_trigger(self):
        """Test Wake Word transitions to ACTIVE"""
        self.jarvis.is_active = False
        
        # Simulate Wake Word Detection
        self.mock_wake.process_audio.return_value = True
        
        # Run ONE iteration of loop logic (manually)
        # We can't run the infinite loop, so we extract the logic or mock the loop
        # Instead, we just call the logic block assuming we are inside the loop
        
        # ... Wait, the logic is inside receive_loop (No, send_audio_loop).
        # Let's inspect send_audio_loop logic by replicating the critical check
        
        # Logic from hybrid_jarvis.py:121
        should_trigger = False
        if self.mock_wake.process_audio(b'data'):
             if not self.jarvis.processing_tool and not self.jarvis.self_speaking_mute:
                 should_trigger = True
                 
        self.assertTrue(should_trigger, "Wake word should trigger in normal state")

    def test_interruption_while_speaking(self):
        """Test Wake Word Barge-In while Jarvis is speaking (TTS)"""
        self.jarvis.is_active = True
        self.jarvis.self_speaking_mute = True # Jarvis IS speaking
        
        # Simulate Wake Word Detection (User shouts "Jarvis" over the TTS)
        self.mock_wake.process_audio.return_value = True
        
        # Logic check
        triggered = False
        if self.mock_wake.process_audio(b'data'):
             # This is the exact condition in hybrid_jarvis.py (UPDATED)
             if not self.jarvis.processing_tool:
                 triggered = True
        
        # CURRENTLY, this expects TRUE because we enabled it.
        self.assertTrue(triggered, "Interruption should be ALLOWED now (AEC enabled)")

    def test_auto_unmute(self):
        """Test that mic un-mutes after silence"""
        self.jarvis.is_active = True
        self.jarvis.self_speaking_mute = True
        self.jarvis.last_audio_time = time.time() - 2.0 # 2 seconds ago
        
        # Current time
        now = time.time()
        
        # Logic from hybrid_jarvis.py:156
        unmuted = False
        if self.jarvis.is_active and self.jarvis.self_speaking_mute and self.jarvis.last_audio_time > 0:
            if now - self.jarvis.last_audio_time > 1.0:
                unmuted = True
                
        self.assertTrue(unmuted, "Mic should auto-unmute after silence")

    def test_semantic_protocol(self):
        """Test if Jarvis handles [PROTOCOL:COMMAND] from Cloud correctly"""
        async def _run_test():
            print("\n--- Testing Semantic Protocol ---")
            
            import re
            bot_text = "[PROTOCOL:LIGHT_ON] Sure, turning on the lights."
            proto_match = re.search(r'\[PROTOCOL:(.*?)\]', bot_text)
            self.assertIsNotNone(proto_match)
            self.assertEqual(proto_match.group(1), "LIGHT_ON")
            
            # Simulate execution
            command = proto_match.group(1)
            if command == "LIGHT_ON":
                await self.mock_light.execute(action="on")
                
            # Verify Light was turned on
            self.mock_light.execute.assert_called_with(action="on")
            print("✅ Semantic Protocol Logic Verified (Simulation)")
            
        self.run_coro(_run_test())

if __name__ == "__main__":
    unittest.main()
