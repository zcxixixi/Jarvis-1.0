"""
Wake Word Detector using OpenWakeWord (Hey Jarvis v0.1)
Strict model-based detection to avoid false triggers.
"""
import numpy as np
import os
import time

class WakeWordDetector:
    """Wake word detector using official hey_jarvis model"""
    
    def __init__(self):
        self.oww_model = None
        self._initialized = False
        self._last_trigger_time = 0
        self._lockout_duration = 1.5 # seconds to ignore audio after trigger
        
    def initialize(self):
        """Initialize OpenWakeWord engine with specific model path"""
        try:
            import openwakeword
            from openwakeword.model import Model
            
            # Use absolute path to the verified model
            model_path = "/Users/kaijimima1234/Desktop/jarvis/venv/lib/python3.12/site-packages/openwakeword/resources/models/hey_jarvis_v0.1.onnx"
            
            if not os.path.exists(model_path):
                print(f"❌ Model file not found at {model_path}")
                return False

            self.oww_model = Model(
                wakeword_models=[model_path],
                inference_framework="onnx"
            )
            self._initialized = True
            print(f"🎙️ OpenWakeWord initialized strictly with: {os.path.basename(model_path)}")
            return True
            
        except Exception as e:
            print(f"❌ OpenWakeWord failed to load: {e}")
            self._initialized = False
            return False
    
    def reset(self):
        """Reset internal model state to prevent 'sticky' detections"""
        if self._initialized and self.oww_model:
            # openwakeword.Model doesn't have a direct reset, 
            # but we can clear its internal state buffers by re-initializing 
            # or just clearing our own trigger logic.
            # Some versions have .reset(), check safely:
            if hasattr(self.oww_model, 'reset'):
                self.oww_model.reset()
            self._last_trigger_time = time.time()
            
    def process_audio(self, audio_data: bytes, threshold: float = 0.5) -> bool:
        if not self._initialized or not self.oww_model:
            return False
            
        # Lockout window to prevent re-triggering on the word 'Jarvis' itself
        if time.time() - self._last_trigger_time < self._lockout_duration:
            return False
            
        try:
            pcm = np.frombuffer(audio_data, dtype=np.int16)
            
            # Run prediction
            prediction = self.oww_model.predict(pcm)
            
            score = 0
            for key, val in prediction.items():
                if "hey_jarvis" in key.lower():
                    score = max(score, val)
            
            if score > threshold:
                print(f"\n🎤 Wake Word Detected! (Score: {score:.2f})")
                self._last_trigger_time = time.time()
                return True
                    
        except Exception:
            pass
            
        return False
    
    def cleanup(self):
        self.oww_model = None
        self._initialized = False

_detector = None
def get_wake_word_detector() -> WakeWordDetector:
    global _detector
    if _detector is None:
        _detector = WakeWordDetector()
    return _detector
