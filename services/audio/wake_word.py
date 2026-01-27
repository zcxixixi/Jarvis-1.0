"""
Wake Word Detector using OpenWakeWord (Fully Open Source, No API Key needed)
Enables voice interruption during music playback
"""
import os
from typing import Optional
import numpy as np
import openwakeword
from openwakeword.model import Model

class WakeWordDetector:
    """Wake word detector using openWakeWord 'jarvis' model"""
    
    def __init__(self):
        self.oww_model = None
        self._initialized = False
        
    def initialize(self):
        """Initialize OpenWakeWord engine"""
        try:
            # Load openWakeWord model (auto-download if needed)
            import openwakeword.utils

            # Download 'hey_jarvis' model if missing
            openwakeword.utils.download_models(["hey_jarvis_v0.1"])

            # Initialize with default path handling
            self.oww_model = Model(
                wakeword_models=["hey_jarvis_v0.1"],
                inference_framework="onnx"
            )

            self._initialized = True
            print("🎙️ OpenWakeWord initialized (model: 'hey_jarvis_v0.1')")
            # openWakeWord expects 16kHz audio in 1280 sample chunks (80ms)
            return True
        except Exception as e:
            print(f"❌ Failed to initialize OpenWakeWord: {e}")
            return False
    
    def process_audio(self, audio_data: bytes, threshold: Optional[float] = None) -> bool:
        """
        Process audio chunk and check for wake word.
        
        Args:
            audio_data: Raw PCM audio bytes
            threshold: Optional override for detection threshold
        """
        if not self._initialized or self.oww_model is None:
            return False
            
        try:
            # Convert bytes to float32 or int16 numpy array
            pcm = np.frombuffer(audio_data, dtype=np.int16)
            
            # Predict
            prediction = self.oww_model.predict(pcm)
            if isinstance(prediction, tuple):
                prediction = prediction[0] if prediction else {}
            
            # Debug: print score if it's significant
            score = prediction.get("hey_jarvis_v0.1", 0)
            if score > 0.01:
                # Reduce log spam
                # print(f"DEBUG: OpenWakeWord Score: {score:.3f}")
                pass
            
            # Check score
            if threshold is None:
                # SENSITIVITY UP: Default 0.3 instead of 0.4
                threshold = float(os.environ.get("WAKE_THRESHOLD", 0.3))
            # The key is the filename without extension
            score = prediction.get("hey_jarvis_v0.1", 0)
            
            if score > threshold:
                print(f"\n🎤 Local Wake: 'JARVIS' detected! (Score: {score:.2f})")
                return True
                    
        except Exception as e:
            # Silently handle audio processing errors in loop
            pass
            
        return False
    
    def cleanup(self):
        """Release resources"""
        # OpenWakeWord handles cleanup via ONNX runtime
        self.oww_model = None
        self._initialized = False

# Singleton instance
_detector = None

def get_wake_word_detector() -> WakeWordDetector:
    """Get singleton wake word detector instance"""
    global _detector
    if _detector is None:
        _detector = WakeWordDetector()
    return _detector
