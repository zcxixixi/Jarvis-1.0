
import os
import subprocess
import time
import sys

def check_permission():
    """Checks if screen recording permission is granted using peekaboo."""
    try:
        result = subprocess.run(["peekaboo", "permissions"], capture_output=True, text=True)
        return "Screen Recording (Required): Granted" in result.stdout
    except:
        return False

def trigger_prompt():
    """Attempts a screen capture to trigger the macOS permission dialog."""
    print("🚀 Attempting to trigger macOS Screen Recording prompt...")
    # Using the native screencapture utility to trigger the OS dialog
    subprocess.run(["/usr/sbin/screencapture", "-c"], capture_output=True)

def main():
    print("=== Jarvis Screen Access Setup ===")
    
    if check_permission():
        print("✅ Permission is already GRANTED.")
        return

    trigger_prompt()
    
    print("\n📬 A system dialog should have appeared asking for Screen Recording permission.")
    print("👉 Please go to: System Settings > Privacy & Security > Screen Recording")
    print("👉 Enable permission for your Terminal / Python application.")
    print("\n⏳ Waiting for you to grant permission (Ctrl+C to stop)...")
    
    try:
        while not check_permission():
            time.sleep(2)
            sys.stdout.write(".")
            sys.stdout.flush()
        
        print("\n\n🎉 SUCCESS! Screen Recording permission has been GRANTED.")
        print("I can now see your screen,先生.")
    except KeyboardInterrupt:
        print("\n\n🛑 Setup interrupted.")

if __name__ == "__main__":
    main()
