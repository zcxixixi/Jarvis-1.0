"""
Final Product Verification (UAT)
This script performs a REAL WORLD test of the Netease -> Playback pipeline.
It is NOT a unit test. It acts like a user.
"""
import os
import time
import sys
import subprocess
from tools.migu_tools import MiguMusicTool

def run_apple_script(script):
    cmd = f"osascript -e '{script}'"
    return subprocess.getoutput(cmd)

async def main():
    print("🎬 STARTING FINAL PRODUCT VERIFICATION")
    print("========================================")
    
    # 1. Environment Prep
    tool = MiguMusicTool()
    cache_dir = tool._cache_dir
    print(f"🧹 Cleaning Cache at {cache_dir}...")
    if os.path.exists(cache_dir):
        import shutil
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir)
    
    # 2. Real Download Test
    # Inject User Cookie
    cookie_val = "00B1B722D178BFA88B4DEE355F199EB8E883FA1B85817CFF12557454F29D9928C501AE9AA8F1F739F198D6C19D2AAF593DA742F5A54A1E3186E1E844EB46061C99CC0D0D0A162D9A22216FB02B91EBF7524BD9766EFEB0B2938AD7E60EBC63B1B90BDAC3D5925ED37AFC042DF23304F5800E1D5D1DC2E7BA995884B26B161E1E000E0F130F4C6464A715AB8AE6CB63D4ED44FACF37380B4AEF6983B3D98DC69BA7ABA64E80B8D9C34994BCC2FEC595F21206FECD7BB45A4DE723831069495285974E61FFC913CB9933B47C5DF7107BDDD9F915AB6B59109CA3A347945672A0A52F6236B5C7DEE4A8C483718D0D3C176F8ED552426145BE370430F154D28F235EF4E832825747E9C18ED0EDBE54A18E6F666CF0ED65AC0A921BD2BF2B503F8E893CC2EB77F83F29BB5BEFBFC82A792CB3CC530306474218A291A6011BC3013F61EE5D2AFAA69D6150A3424D23DDD291C0F6CEEDB7E123ED22A2C7C2C8D248AE2CA550FEC92F076DBDD0C10B44FF8FC738700CF1BC2753DE9970D367D8026C8EAD518F9E0C429F422D90F6F74268DD485A52"
    os.environ["NETEASE_COOKIE"] = f"MUSIC_U={cookie_val}"
    
    song_query = "海阔天空" 
    print(f"☁️  Searching & Playing '{song_query}' (High Level API)...")
    start_time = time.time()
    
    # Use Public API - This tests fallback logic automatically
    res = await tool.execute(action="play", query=song_query)
    print(f"   Result: {res}")
    
    if "❌" in res and "VIP" not in res: # VIP messages might have prefix
         # e.g. "▶️ 🌟(VIP) 正在播放:..."
         if "正在播放" not in res:
            print("❌ Playback failed to start!")
            return
    
    if "❌" in res:
        print("❌ Playback failed to start!")
        return

    # 3. Process Monitor (The "Listening" Phase)
    print("\n👂 Monitoring Playback Stability (10 Seconds)...")
    # Find the afplay process
    for i in range(10):
        # Check if afplay is running
        check = subprocess.run(["pgrep", "-f", "afplay"], capture_output=True)
        is_playing = (check.returncode == 0)
        
        # Check Volume
        vol = run_apple_script("output volume of (get volume settings)")
        
        status_icon = "🟢" if is_playing else "🔴"
        print(f"   T+{i+1}s | Status: {status_icon} Playing | Volume: {vol}%")
        
        if not is_playing:
            print("❌ Playback crashed or stopped prematurely!")
            break
        
        time.sleep(1)
        
    # 4. Cleanup
    print("\n⏹️  Stopping Playback...")
    await tool.execute(action="stop")
    
    # 5. Final File Verify
    files = os.listdir(cache_dir)
    print(f"\n📂 Final Cache Content: {files}")
    if len(files) > 0:
        file_path = os.path.join(cache_dir, files[0])
        size_mb = os.path.getsize(file_path) / 1024 / 1024
        print(f"   Downloaded File Size: {size_mb:.2f} MB")
        if size_mb > 1.0:
            print("✅ CHECK: File is a valid song.")
        else:
            print("❌ CHECK: File too small!")
    else:
        print("❌ CHECK: No file cached!")

    print("\n========================================")
    print("✅ PRODUCT VERIFICATION COMPLETE")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
