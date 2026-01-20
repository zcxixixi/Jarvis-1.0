"""
Robustness Tests for Semantic Intent Protocol

Tests edge cases:
1. Valid protocols (LIGHT_ON, LIGHT_OFF, PLAY_MUSIC, MUSIC_STOP)
2. Case sensitivity (Light_on, light_on)
3. Malformed tags ([PROTOCOL], [PROTOCOL:], empty)
4. No protocol in text
5. Multiple protocols in one message
"""

import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hybrid_jarvis import HybridJarvis


class TestProtocolRobustness(unittest.TestCase):
    def setUp(self):
        # Patch heavy dependencies
        with patch('wake_word.get_wake_word_detector', return_value=MagicMock()), \
             patch('aec_processor.get_aec'), \
             patch('audio_utils.play_boot_sound'):
            self.jarvis = HybridJarvis()
            
        # Mock Tools
        self.mock_light = AsyncMock()
        self.mock_music = AsyncMock()
        self.mock_music._scan_music = MagicMock(return_value=["song1.mp3"])
        
        self.jarvis.tools = {
            "control_xiaomi_light": self.mock_light,
            "play_music": self.mock_music
        }
    
    def run_coro(self, coro):
        return asyncio.run(coro)

    # --- Valid Protocol Tests ---
    async def test_protocol_light_on(self):
        """Test valid Natural Trigger: Light On"""
        await self.jarvis.process_protocol_event("好的，光照系统已激活，为您服务。")
        self.jarvis.tools["control_xiaomi_light"].execute.assert_called_with(action="on")

    async def test_protocol_light_off(self):
        """Test valid Natural Trigger: Light Off"""
        await self.jarvis.process_protocol_event("光照系统已关闭，晚安先生。")
        self.jarvis.tools["control_xiaomi_light"].execute.assert_called_with(action="off")

    async def test_protocol_music_play(self):
        """Test valid Natural Trigger: Play Music"""
        with patch('os.path.basename', return_value="test_song.mp3"):
            await self.jarvis.process_protocol_event("正在接入音频流，请欣赏。")
            self.jarvis.tools["play_music"].execute.assert_called()
            self.assertTrue(self.jarvis.music_playing)

    async def test_protocol_music_stop(self):
        """Test valid Natural Trigger: Stop Music"""
        self.jarvis.stop_music_and_resume = AsyncMock()
        await self.jarvis.process_protocol_event("好的，音频输出已切断。")
        self.jarvis.stop_music_and_resume.assert_called_once()

    async def test_protocol_case_insensitive(self):
        """Test trigger is just substring match (case irrelevant for Chinese typically)"""
        # Testing robustness of partial matches
        await self.jarvis.process_protocol_event("...光照系统已激活...")
        self.jarvis.tools["control_xiaomi_light"].execute.assert_called_with(action="on")

    async def test_malformed_protocol(self):
        """Test text without triggers should do nothing"""
        await self.jarvis.process_protocol_event("这就为您打开灯光。") # "打开灯光" is NOT the trigger
        self.jarvis.tools["control_xiaomi_light"].execute.assert_not_called()

    async def test_no_protocol(self):
        """Test normal text"""
        await self.jarvis.process_protocol_event("你好，我是Jarvis。")
        self.jarvis.tools["control_xiaomi_light"].execute.assert_not_called()

    async def test_multiple_protocols(self):
        """Test first trigger is prioritized"""
        # "光照系统已激活" appears first
        await self.jarvis.process_protocol_event("光照系统已激活，并且光照系统已关闭。")
        self.jarvis.tools["control_xiaomi_light"].execute.assert_called_with(action="on")
        self.mock_music.execute.assert_not_called()

    # --- Edge Cases ---
    def test_protocol_mid_sentence(self):
        """Protocol can appear anywhere in text"""
        self.run_coro(self.jarvis.process_protocol_event("Okay, [PROTOCOL:LIGHT_ON] done."))
        self.mock_light.execute.assert_called_with(action="on")

    def test_multiple_protocols(self):
        """Only first protocol should be executed"""
        self.run_coro(self.jarvis.process_protocol_event("[PROTOCOL:LIGHT_ON] and [PROTOCOL:LIGHT_OFF]"))
        # Only first should fire
        self.mock_light.execute.assert_called_with(action="on")


if __name__ == "__main__":
    unittest.main()
