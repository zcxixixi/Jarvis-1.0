
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hybrid_jarvis import HybridJarvis

class TestJarvisIntents(unittest.TestCase):
    def setUp(self):
        # Initialize Jarvis without networking
        self.jarvis = HybridJarvis()
        
        # Mock the tools dictionary
        self.mock_music = AsyncMock()
        self.mock_music.execute.return_value = "Music Playing"
        self.mock_weather = AsyncMock()
        self.mock_weather.execute.return_value = "Weather Info"
        self.mock_light = AsyncMock()
        self.mock_light.execute.return_value = "Light toggled"
        
        # Inject mocks
        self.jarvis.tools["play_music"] = self.mock_music
        self.jarvis.tools["get_weather"] = self.mock_weather
        self.jarvis.tools["control_xiaomi_light"] = self.mock_light
        
        # Mock send_text_query to avoid network
        self.jarvis.send_text_query = AsyncMock()

        # Mock _scan_music (Synchronous)
        self.mock_music._scan_music = MagicMock(return_value=["test_song.mp3"])

    def run_async(self, coroutine):
        return asyncio.run(coroutine)

    def test_music_intent_generic(self):
        """Test generic music commands"""
        inputs = ["来首音乐", "播放", "我要听歌", "随便放首"]
        for text in inputs:
            self.run_async(self.jarvis.check_and_run_tool(text))
            # Should call scan_music (generic) logic which calls execute with generic query
            # Because scan_music is internal, we check if execute was called at all
            self.assertTrue(self.mock_music.execute.called, f"Failed for '{text}'")
            self.mock_music.execute.reset_mock()

    def test_music_intent_specific(self):
        """Test specific song requests"""
        text = "播放周杰伦的七里香"
        self.run_async(self.jarvis.check_and_run_tool(text))
        
        # Check arguments
        args, kwargs = self.mock_music.execute.call_args
        self.assertIn(kwargs.get('query'), ["周杰伦的七里香", "七里香", "周杰伦七里香"])
        self.assertEqual(kwargs.get('action'), "play")

    def test_stop_command(self):
        """Test stop/pause priority"""
        text = "把它关掉"
        self.run_async(self.jarvis.check_and_run_tool(text))
        
        self.mock_music.execute.assert_called_with(action="stop")

    def test_weather_city_extraction(self):
        """Test city extraction logic"""
        # Case 1: Simple
        self.run_async(self.jarvis.check_and_run_tool("北京天气"))
        self.mock_weather.execute.assert_called_with(city="北京") 
        
        # Case 2: Complex
        self.run_async(self.jarvis.check_and_run_tool("帮我查一下上海明天的天气怎么样"))
        args, kwargs = self.mock_weather.execute.call_args
        self.assertIn("上海", kwargs.get('city'))

    def test_light_control(self):
        """Test light control extraction"""
        self.run_async(self.jarvis.check_and_run_tool("把灯打开"))
        args, kwargs = self.mock_light.execute.call_args
        self.assertEqual(kwargs.get('action'), "on")

        self.run_async(self.jarvis.check_and_run_tool("关灯"))
        args, kwargs = self.mock_light.execute.call_args
        self.assertEqual(kwargs.get('action'), "off")

    def test_news_intent(self):
        """Test news intent extraction"""
        # Patch the info_tools inside hybrid_jarvis is tricky because it's imported inside the function
        # But for 'check_and_run_tool', we can mock the module in sys.modules or patch where it's used.
        # However, since correct logic path prints 'Detected Intent: get_news', we can check stdout or side effects.
        # But better: Mock 'send_text_query' and check if it was called with a prompt containing '新闻'.
        
        # We need to mock info_tools.get_news_briefing return value
        with patch('tools.info_tools.get_news_briefing', new=AsyncMock(return_value="News Summary")):
            self.run_async(self.jarvis.check_and_run_tool("今天有什么大新闻"))
            
            # Check if send_text_query was called
            self.assertTrue(self.jarvis.send_text_query.called)
            call_args = self.jarvis.send_text_query.call_args[0][0]
            self.assertIn("News Summary", call_args)

    def test_stock_intent(self):
        """Test stock intent extraction"""
        with patch('tools.info_tools.get_stock_price', new=AsyncMock(return_value="Stock Price Info")):
            # Case 1: Suffix
            self.run_async(self.jarvis.check_and_run_tool("查一下苹果股价"))
            self.assertTrue(self.jarvis.send_text_query.called)
            call_args = self.jarvis.send_text_query.call_args[0][0]
            self.assertIn("用户查询了股价", call_args)
            self.assertIn("Stock Price Info", call_args)
            
            # Reset
            self.jarvis.send_text_query.reset_mock()
            
            # Case 2: Mapping check (茅台)
            self.run_async(self.jarvis.check_and_run_tool("茅台行情怎么样"))
            call_args = self.jarvis.send_text_query.call_args[0][0]
            self.assertIn("Stock Price Info", call_args)

if __name__ == '__main__':
    unittest.main()
