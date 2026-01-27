"""
Audio utilities for Jarvis
- Wake sound generation
- Volume control
"""
import subprocess
import os
import math
import wave
import struct
import platform
import re

# Path for generated sounds
SOUND_DIR = os.path.expanduser("~/Music/JarvisCache/sounds")
if platform.system() != "Darwin":
    # On Pi, put it in the project dir or home
    SOUND_DIR = os.path.expanduser("~/jarvis_sounds")

def ensure_sound_dir():
    if not os.path.exists(SOUND_DIR):
        os.makedirs(SOUND_DIR)

def generate_wake_sound():
    """
    生成一个极短、清脆的单声提示音 (0.12秒)，这是备用方案。
    主要的提示音应该来自 voice/ 文件夹下的 MP3。
    """
    ensure_sound_dir()
    
    default_path = os.path.join(SOUND_DIR, "wake_scifi.wav")
    
    # ⚠️ 强制覆盖逻辑：为了确保你下次听到的是新声音
    if os.path.exists(default_path):
        os.remove(default_path)
    
    print("✨ Generating backup Single-Click wake sound (Iron Man Style)...")
    
    import wave
    import math
    import struct
    
    sample_rate = 44100
    duration = 0.12  # 只有 0.12 秒
    
    with wave.open(default_path, 'w') as wav_file:
        wav_file.setnchannels(1) 
        wav_file.setsampwidth(2) 
        wav_file.setframerate(sample_rate)
        
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            
            # 🎵 声音设计：快速上滑音 (800Hz -> 1800Hz)
            freq = 800 + (1000 * (t / duration))
            val = math.sin(2 * math.pi * freq * t)
            
            # 📉 包络设计 (Envelope)：
            if t < 0.01:
                env = t / 0.01
            else:
                env = math.exp(-(t - 0.01) * 25)
            
            value = int(32767 * 0.9 * env * val)
            wav_file.writeframes(struct.pack('<h', value))
            
    return default_path

def ensure_wake_sounds():
    """Ensure the single wake sound exists"""
    generate_wake_sound()

# Path for mp3/mp4 voice files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WAKE_SOUND_DIR = os.path.join(BASE_DIR, "voice")
WAKE_SOUND_INDEX = 0

def get_audio_duration(file_path):
    """Get duration of a WAV or MP3 file in seconds"""
    try:
        import wave
        if file_path.endswith('.wav'):
            with wave.open(file_path, 'r') as f:
                frames = f.getnframes()
                rate = f.getframerate()
                return frames / float(rate)
        elif file_path.endswith('.mp3'):
            # Fallback for MP3 (approximate based on bitrate if needed, or just 1.5s)
            return 1.5
    except:
        pass
    return 1.0

# Global timestamp for cooldown
LAST_WAKE_TIME = 0

def play_wake_sound():
    """
    Play one of the rotating wake sounds and return its duration.
    """
    global WAKE_SOUND_INDEX, LAST_WAKE_TIME
    
    import time
    now = time.time()
    
    # 🛡️ SMART COOLDOWN: 
    # Use a 1.0s lockout to prevent rapid re-triggering from sticky detection
    if now - LAST_WAKE_TIME < 1.0:
        return 0
        
    LAST_WAKE_TIME = now
    
    # Random selection 1-4
    import random
    idx = random.randint(1, 4)
    
    # Priority:
    # 1. Custom WAV (Full length user sounds)
    sound_file = os.path.join(WAKE_SOUND_DIR, f"{idx}.wav")
    
    # 2. Fallback to MP3
    if not os.path.exists(sound_file):
        sound_file = os.path.join(WAKE_SOUND_DIR, f"{idx}.mp3")
    
    # 3. Last Fallback
    if not os.path.exists(sound_file):
        sound_file = os.path.join(SOUND_DIR, "wake_scifi.wav")
        if not os.path.exists(sound_file):
             return 0

    duration = get_audio_duration(sound_file)
    print(f"🔊 Playing Wake Sound: {os.path.basename(sound_file)} ({duration:.2f}s)")

    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["afplay", sound_file], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
        else:
            if sound_file.endswith(".wav"):
                # Use aplay for ALSA (bluealsa compatible)
                subprocess.Popen(["aplay", "-q", sound_file],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            elif sound_file.endswith(".mp3"):
                # Use mpg123 with ALSA backend
                subprocess.Popen(["mpg123", "-o", "alsa", "-q", sound_file],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["aplay", "-q", sound_file],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error playing wake sound: {e}")
        return 0
        
    return duration

def play_boot_sound():
    """Play the custom boot sound"""
    boot_file = os.path.join(WAKE_SOUND_DIR, "open_voice.mp4")
    if not os.path.exists(boot_file):
        print(f"⚠️ Boot sound not found: {boot_file}")
        return
        
    print(f"🎸 Playing boot sequence: {os.path.basename(boot_file)}")
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["afplay", boot_file], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
        else:
            # Use mpv for mp4 audio with ALSA backend
            subprocess.Popen(["mpv", "--ao=alsa", "--no-video", "--really-quiet", boot_file],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Could not play boot sound: {e}")

def get_system_volume():
    """Get system volume (0-100)"""
    try:
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["osascript", "-e", "output volume of (get volume settings)"],
                capture_output=True, text=True, check=True
            )
            return int(result.stdout.strip())
        else:
            # Linux: pactl get-sink-volume @DEFAULT_SINK@
            # Output: Volume: front-left: 32768 /  50% / -18.06 dB ...
            result = subprocess.run(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                capture_output=True, text=True, check=True
            )
            # Find the percentage (e.g., 50%)
            match = re.search(r"(\d+)%", result.stdout)
            if match:
                return int(match.group(1))
    except:
        pass
    return 50

def set_system_volume(percent: int):
    """Set system volume (0-100)"""
    try:
        if platform.system() == "Darwin":
            subprocess.run(
                ["osascript", "-e", f"set volume output volume {percent}"],
                check=True, capture_output=True
            )
            return True
        else:
            # Linux: pactl set-sink-volume @DEFAULT_SINK@ 50%
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"], 
                         check=True, capture_output=True)
            return True
    except:
        pass
    return False

# Persistent state for volume ducking
# We default to 80 on first boot, but will update dynamically
ORIGINAL_VOLUME = 80  
IS_DUCKED = False

def lower_music_volume():
    """Duck volume for listening/speaking (System master volume)"""
    global ORIGINAL_VOLUME, IS_DUCKED
    
    # Don't double-duck
    if IS_DUCKED:
        return
        
    current = get_system_volume()
    # Save the current volume regardless of level
    ORIGINAL_VOLUME = current
    
    # Target volume for Jarvis conversation:
    # If currently >50, drop to 30. If already <30, drop slightly more or stay.
    target = 30
    if current <= 35:
        target = max(15, current - 15)
        
    print(f"🔇 Ducking volume: {current}% -> {target}%")
    set_system_volume(target)
    IS_DUCKED = True

def restore_music_volume():
    """Restore volume after conversation to exactly what it was"""
    global ORIGINAL_VOLUME, IS_DUCKED
    
    if not IS_DUCKED:
        return True
        
    print(f"🔊 Restoring volume: {ORIGINAL_VOLUME}%")
    set_system_volume(ORIGINAL_VOLUME)
    IS_DUCKED = False
    return True

# Pre-generate wake sound on import
# Pre-generate wake sound on import logic REMOVED to avoid unwanted files
# ensure_wake_sounds() will only be called lazily if play_wake_sound fails to find MP3s
# ensure_wake_sounds()
