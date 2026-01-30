import asyncio
import os
import sys

# Try to import edge_tts
try:
    import edge_tts
except ImportError:
    print("Installing edge-tts...")
    os.system("pip install edge-tts")
    import edge_tts

async def main():
    text = "系统音频测试。如果您能听到这句话，说明扬声器工作正常。我是Jarvis。"
    if len(sys.argv) > 1:
        text = sys.argv[1]
        
    print(f"🎤 Generating Audio (EdgeTTS): '{text}'...")
    output_file = "/tmp/jarvis_edge_test.mp3"
    
    communicate = edge_tts.Communicate(text, "zh-CN-YunxiNeural")
    await communicate.save(output_file)
    
    print(f"💾 Saved to {output_file}")
    
    # Play Audio
    print("🔊 Playing audio...")
    # Try afplay (macOS)
    ret = os.system(f"afplay {output_file}")
    if ret != 0:
        # Try mpv
        ret = os.system(f"mpv --no-video {output_file}")
        if ret != 0:
            print("❌ Could not play audio. Please check 'afplay' or install 'mpv'.")

if __name__ == "__main__":
    asyncio.run(main())
