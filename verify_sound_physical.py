"""
Physical Sound Verification
1. Unmutes system
2. Sets volume to 50%
3. Checks audio file validity
4. Plays sound in foreground to confirm output
"""
import os
import subprocess
import time
import sys

def run_apple_script(script):
    cmd = f"osascript -e '{script}'"
    return subprocess.getoutput(cmd)

def check_system_audio():
    print("🔊 Checking System Audio Settings...")
    
    # 1. Unmute
    run_apple_script("set volume output muted false")
    print("   [Action] Unmuted system")
    
    # 2. Set Volume
    current_vol = run_apple_script("output volume of (get volume settings)")
    print(f"   [Status] Current Volume: {current_vol}%")
    
    if int(current_vol) < 20:
        run_apple_script("set volume output volume 50")
        print("   [Action] Volume forced to 50%")
    else:
        print("   [OK] Volume is adequate")

def verify_file(path):
    print(f"\n📂 Checking Audio File: {path}")
    if not os.path.exists(path):
        print("   [FAIL] File does not exist!")
        return False
        
    size = os.path.getsize(path)
    print(f"   [Info] Size: {size / 1024 / 1024:.2f} MB")
    
    if size < 1000:
        print("   [FAIL] File too small (likely corrupted download)")
        return False
        
    print("   [OK] File looks valid")
    return True

def play_test_sound(path):
    print("\n🎵 Attempting Playback (Foregound)...")
    print("   Command: /usr/bin/afplay -v 1 -t 5 " + path)
    
    # Run afplay for 5 seconds
    # -v 1: Volume high
    # -t 5: Play 5 seconds
    try:
        proc = subprocess.run(
            ["/usr/bin/afplay", "-v", "1", "-t", "5", path],
            capture_output=True,
            text=True
        )
        
        if proc.returncode == 0:
            print(f"   [PASS] Player exited normally.")
            print("   (If you didn't hear audio, verify output device selection in System Settings)")
        else:
            print(f"   [FAIL] Player Error: {proc.stderr}")
            
    except Exception as e:
        print(f"   [CRITICAL] Execution failed: {e}")

if __name__ == "__main__":
    test_file = os.path.expanduser("~/Music/test_song.mp3")
    
    check_system_audio()
    if verify_file(test_file):
        play_test_sound(test_file)
