"""
Wake Word Detector using Porcupine
Enables voice interruption during music playback
"""
import pvporcupine
import struct
import os

# Your Picovoice Access Key
PORCUPINE_ACCESS_KEY = "ZAxC/tIzFFgUHhUCBdH+Aw8P+y17v+hCl9D+g4v9HE3iwk8qV2dKuQ=="

class WakeWordDetector:
    """Lightweight wake word detector for 'jarvis' keyword"""
    
    def __init__(self):
        self.porcupine = None
        self._initialized = False
        
    def initialize(self):
        """Initialize Porcupine engine"""
        try:
            self.porcupine = pvporcupine.create(
                access_key=PORCUPINE_ACCESS_KEY,
                keywords=["jarvis"],
                sensitivities=[1.0] # Set to MAXIMUM sensitivity for easiest interruption
            )
            self._initialized = True
            print(f"🎙️ Wake word detector initialized (keyword: 'jarvis')")
            print(f"   Sample rate: {self.porcupine.sample_rate} Hz")
            print(f"   Frame length: {self.porcupine.frame_length} samples")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize wake word detector: {e}")
            return False
    
    def process_audio(self, audio_data: bytes) -> bool:
        """
        Process audio chunk and check for wake word.
        
        Args:
            audio_data: Raw PCM audio bytes (16-bit signed, mono, 16kHz)
            
        Returns:
            True if wake word detected, False otherwise
        """
        if not self._initialized or self.porcupine is None:
            return False
            
        try:
            # Convert bytes to int16 array
            # Porcupine expects frame_length samples
            frame_length = self.porcupine.frame_length
            
            # Unpack audio data
            num_samples = len(audio_data) // 2  # 2 bytes per sample (16-bit)
            pcm = struct.unpack_from(f"{num_samples}h", audio_data)
            
            # Process in chunks of frame_length
            for i in range(0, len(pcm) - frame_length + 1, frame_length):
                frame = pcm[i:i + frame_length]
                keyword_index = self.porcupine.process(frame)
                
                if keyword_index >= 0:
                    print("\n🎤 Wake word 'JARVIS' detected!")
                    return True
                    
        except Exception as e:
            # Silently handle audio processing errors
            pass
            
        return False
    
    def cleanup(self):
        """Release resources"""
        if self.porcupine is not None:
            self.porcupine.delete()
            self.porcupine = None
            self._initialized = False

# Singleton instance
_detector = None

def get_wake_word_detector() -> WakeWordDetector:
    """Get singleton wake word detector instance"""
    global _detector
    if _detector is None:
        _detector = WakeWordDetector()
    return _detector
