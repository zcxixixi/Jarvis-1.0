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

# Path for generated sounds
SOUND_DIR = os.path.expanduser("~/Music/JarvisCache/sounds")

def ensure_sound_dir():
    if not os.path.exists(SOUND_DIR):
        os.makedirs(SOUND_DIR)

def generate_wake_sound():
    """Generate a high-tech sci-fi double-chirp sound for wake activation (only if missing)"""
    ensure_sound_dir()
    
    custom_path = os.path.join(SOUND_DIR, "custom_wake.wav")
    default_path = os.path.join(SOUND_DIR, "wake_scifi.wav")
    
    # Prioritize user-provided custom sound
    if os.path.exists(custom_path):
        return custom_path
        
    # If default exists, don't overwrite it (allows user to replace wake_scifi.wav directly)
    if os.path.exists(default_path):
        return default_path
    
    # Otherwise, generate our sci-fi sound as a placeholder
    sample_rate = 44100
    duration = 0.5  # seconds
    import random
    
    with wave.open(default_path, 'w') as wav_file:
        wav_file.setnchannels(1) 
        wav_file.setsampwidth(2) 
        wav_file.setframerate(sample_rate)
        
        n_samples = int(sample_rate * duration)
        for i in range(n_samples):
            t = i / sample_rate
            
            # Pulse 1 (0.0 to 0.15s)
            env = 0
            val = 0
            if 0 <= t <= 0.15:
                freq = 1800 * math.pow(1.5, t / 0.15)
                env = math.sin(math.pi * t / 0.15)
                val = (math.sin(2 * math.pi * freq * t) * 0.5 + 
                       (1.0 if math.sin(2 * math.pi * freq * 2 * t) > 0 else -1.0) * 0.1 + 
                       (random.random() * 2 - 1) * 0.05)
            # Pulse 2 (0.18 to 0.35s)
            elif 0.18 <= t <= 0.35:
                t_rel = t - 0.18
                freq = 2400 * math.pow(1.2, t_rel / 0.17)
                env = math.sin(math.pi * t_rel / 0.17)
                val = (math.sin(2 * math.pi * freq * t) * 0.5 + 
                       (random.random() * 2 - 1) * 0.08)
            # Decay
            elif 0.35 < t <= 0.5:
                t_rel = t - 0.35
                env = 0.2 * (1.0 - t_rel / 0.15)
                val = math.sin(2 * math.pi * 3000 * t) * (random.random() * 0.5)
            
            value = int(32767 * 0.7 * env * val)
            wav_file.writeframes(struct.pack('<h', value))
    
    print(f"✨ Default sci-fi sound created: {default_path}")
    return default_path

# State for rotating wake sounds
WAKE_SOUND_INDEX = 0
WAKE_SOUND_DIR = "/Users/kaijimima1234/Desktop/jarvis/voice"

def play_wake_sound():
    """Play one of the rotating wake sounds (1.mp3, 2.mp3, etc.)"""
    global WAKE_SOUND_INDEX
    
    # Files are 1.mp3, 2.mp3, 3.mp3, 4.mp3
    WAKE_SOUND_INDEX = (WAKE_SOUND_INDEX % 4) + 1
    sound_file = os.path.join(WAKE_SOUND_DIR, f"{WAKE_SOUND_INDEX}.mp3")
    
    # Fallback to generated sound if files are missing
    if not os.path.exists(sound_file):
        sound_file = generate_wake_sound()
        
    try:
        import platform
        if platform.system() == "Darwin":
            subprocess.Popen(["afplay", sound_file], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
        else:
            # For MP3 on Linux, mpg123 is usually best
            subprocess.Popen(["mpg123", "-q", sound_file],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Could not play wake sound: {e}")

def play_boot_sound():
    """Play the custom boot sound (mp4 audio)"""
    boot_file = "/Users/kaijimima1234/Desktop/jarvis/voice/open_voice.mp4"
    if not os.path.exists(boot_file):
        return
        
    print(f"🎸 Playing boot sequence: {os.path.basename(boot_file)}")
    try:
        import platform
        if platform.system() == "Darwin":
            # afplay handles mp4 audio tracks natively on macOS
            subprocess.Popen(["afplay", boot_file], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
        else:
            # Fallback for Linux usually requires ffplay
            subprocess.Popen(["ffplay", "-nodisp", "-autoexit", boot_file],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Could not play boot sound: {e}")

def get_system_volume():
    """Get current macOS system volume (0-100)"""
    try:
        import platform
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["osascript", "-e", "output volume of (get volume settings)"],
                capture_output=True, text=True, check=True
            )
            return int(result.stdout.strip())
    except:
        pass
    return 50 # Fallback

def set_system_volume(percent: int):
    """Set macOS system volume (0-100)"""
    try:
        import platform
        if platform.system() == "Darwin":
            subprocess.run(
                ["osascript", "-e", f"set volume output volume {percent}"],
                check=True, capture_output=True
            )
            return True
    except:
        pass
    return False

# Persistent state for volume ducking
ORIGINAL_VOLUME = None

def lower_music_volume():
    """Ducking: Lower volume to 15% for voice interaction"""
    global ORIGINAL_VOLUME
    curr = get_system_volume()
    # Only store if we haven't already
    if ORIGINAL_VOLUME is None:
        ORIGINAL_VOLUME = curr
    
    # Duck to 15%
    return set_system_volume(15)

def restore_music_volume():
    """Unducking: Restore to the user's previous volume level"""
    global ORIGINAL_VOLUME
    if ORIGINAL_VOLUME is not None:
        status = set_system_volume(ORIGINAL_VOLUME)
        ORIGINAL_VOLUME = None
        return status
    return True

# Pre-generate wake sound on import
generate_wake_sound()
