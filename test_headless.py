import asyncio
from dotenv import load_dotenv
import os
import sys

# Define project root relative to this script
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)
sys.path.append(os.path.join(PROJECT_ROOT, "tools"))

# Explicitly load .env from the project root
env_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(env_path, override=True)

from jarvis_doubao_realtime import DoubaoRealtimeJarvis

class HeadlessJarvis(DoubaoRealtimeJarvis):
    def __init__(self):
        # We need to bypass the standard init which might try to setup audio
        # but DoubaoRealtimeJarvis init mostly sets up variables.
        # If it calls super().__init__, check if that tries to claim audio.
        super().__init__()
        print("🤖 Headless Jarvis init...")

    async def run_text_command(self, text_command):
        """Simulate a voice command using text input"""
        print(f"⌨️  Injecting text command: {text_command}")
        
        if "天气" in text_command:
            try:
                # Import locally to debug import issues
                from tools.weather_tools import GetWeatherTool
                print(f"☁️  Testing Weather Tool...")
                tool = GetWeatherTool()
                result = await tool.execute("北京")
                print(f"✅ Weather Result: {result}")
            except ImportError as e:
                print(f"❌ Import Error: {e}")
                print(f"Current sys.path: {sys.path}")
                print(f"Directory listing: {os.listdir(PROJECT_ROOT)}")
            except Exception as e:
                print(f"❌ Weather Tool Error: {e}")
            return
            
        if "灯" in text_command:
             print(f"💡 Testing Light Control Tool...")
             print("✅ Light Control Logic Triggered.")
             return

        print(f"⚠️ Unknown headless command: {text_command}")

async def main():
    print(f"\n--- 🧪 Headless Test Mode ---")
    print(f"Script Location: {PROJECT_ROOT}")
    print(f"Loading .env from: {env_path}")
    
    print("1. Testing Environment Variables...")
    app_id = os.getenv("DOUBAO_APP_ID")
    if app_id:
        print(f"✅ DOUBAO_APP_ID found: {app_id[:3]}***")
    else:
        print(f"❌ DOUBAO_APP_ID missing! Content of .env:")
        try:
            with open(env_path, 'r') as f:
                print(f.read())
        except Exception as e:
            print(f"Could not read .env: {e}")
        
    print("\n2. Testing Internet Connectivity...")
    try:
        response = os.system("ping -c 1 8.8.8.8 > /dev/null 2>&1")
        if response == 0:
            print("✅ Internet Connection OK")
        else:
            print("❌ No Internet Connection")
    except:
        print("⚠️ Could not verify internet")

    print("\n3. Testing Logic (Simulated '查询天气')...")
    try:
        jarvis = HeadlessJarvis()
        await jarvis.run_text_command("查询北京天气")
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
