
import asyncio
import sys
import os

# Add parent dir to path to import tools
sys.path.append(os.getcwd())

from tools.migu_tools import MiguMusicTool
from audio_utils import set_system_volume

async def test_search():
    tool = MiguMusicTool()
    print("🔍 Testing Music Search for '晴天'...")
    result = await tool.execute(action="play", query="晴天")
    print(f"Result: {result}")
    
    if "播放" in result:
        print("✅ Music search & URL retrieval successful!")
    else:
        print("❌ Music search failed.")

    print("\n🔊 Testing Volume Control (setting to 40%)...")
    if set_system_volume(40):
        print("✅ System volume control verified!")
    else:
        print("❌ Volume control failed.")

if __name__ == "__main__":
    asyncio.run(test_search())
