"""
Wake Word Detection using OpenWakeWord
Replaces wake word logic from hybrid_jarvis.py (~150 lines)
"""

import numpy as np
import time
from typing import Optional, List
import os

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import WakeWordConfig

class WakeWordDetector:
    """
    Detects wake words like "Hey Jarvis" using OpenWakeWord.
    
    Features:
    - Local detection (no cloud)
    - Multiple wake word support
    - Configurable threshold
    - Debouncing to prevent double triggers
    
    Usage:
        detector = WakeWordDetector()
        
        for audio_chunk in stream:
            wake_word = detector.detect(audio_chunk)
            if wake_word:
                print(f"Detected: {wake_word}")
    """
    
    def __init__(self, config: WakeWordConfig = None):
        self.config = config or WakeWordConfig()
        
        # Try to load OpenWakeWord
        try:
            import openwakeword
            from openwakeword.model import Model as WakeWordModel
            
            print("Loading OpenWakeWord models...")
            
            # Find model files
            model_paths = self._find_model_files()
            
            if not model_paths:
                print("⚠️ No wake word models found, using keyword matching")
                self.model = None
            else:
                self.model = WakeWordModel(
                    wakeword_models=model_paths,
                    inference_framework='onnx'
                )
                print(f"✅ Loaded {len(model_paths)} wake word models")
            
        except ImportError:
            print("⚠️ OpenWakeWord not installed, using keyword matching")
            self.model = None
        except Exception as e:
            print(f"⚠️ Failed to load OpenWakeWord: {e}")
            self.model = None
        
        # State
        self.last_detection_time = 0.0
        self.detection_count = 0
    
    def _find_model_files(self) -> List[str]:
        """Find wake word model files"""
        model_files = []
        
        # Check for models in common locations
        search_paths = [
            "models/wakeword",
            "jarvis_assistant/models/wakeword",
            os.path.expanduser("~/.cache/openwakeword"),
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.endswith('.onnx') or file.endswith('.tflite'):
                        model_files.append(os.path.join(path, file))
        
        return model_files
    
    def detect(self, audio_chunk: bytes) -> Optional[str]:
        """
        Check if wake word is present in audio chunk.
        
        Args:
            audio_chunk: Raw audio bytes (16-bit PCM, 16kHz)
            
        Returns:
            str: Wake word name if detected, None otherwise
        """
        now = time.time()
        
        # Debounce - ignore detections within debounce window
        if now - self.last_detection_time < self.config.debounce_seconds:
            return None
        
        if self.model is None:
            # Fallback: simple keyword detection from STT
            return None
        
        # Convert to numpy array (float32, normalized -1 to 1)
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        # Run detection
        try:
            predictions = self.model.predict(audio_float32)
            
            # Check all models
            for model_name, score in predictions.items():
                if score > self.config.threshold:
                    self.last_detection_time = now
                    self.detection_count += 1
                    
                    print(f"🎤 Wake word detected: {model_name} (score: {score:.2f})")
                    return model_name
            
        except Exception as e:
            print(f"⚠️ Wake word detection error: {e}")
        
        return None
    
    def detect_from_text(self, text: str) -> bool:
        """
        Fallback: Detect wake word from transcribed text.
        Useful when OpenWakeWord isn't available.
        
        Args:
            text: Transcribed text from STT
            
        Returns:
            bool: True if wake word detected
        """
        text_lower = text.lower()
        
        wake_phrases = [
            "hey jarvis",
            "嘿 jarvis",
            "jarvis",
            "贾维斯",
        ]
        
        for phrase in wake_phrases:
            if phrase in text_lower:
                return True
        
        return False
    
    def reset(self):
        """Reset detection state"""
        self.last_detection_time = 0.0
        self.detection_count = 0
