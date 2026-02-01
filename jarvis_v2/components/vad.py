"""
Voice Activity Detection using Silero VAD
Replaces VAD logic from hybrid_jarvis.py (~100 lines)
"""

import torch
import numpy as np
from typing import List, Tuple, Optional
import warnings

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import VADConfig

# Suppress torch warnings
warnings.filterwarnings('ignore', category=UserWarning, module='torch')

class VoiceActivityDetector:
    """
    Detects speech vs silence using Silero VAD.
    
    Features:
    - ML-based speech detection (better than energy threshold)
    - Configurable thresholds
    - Speech timestamp extraction
    - Handles streaming audio
    
    Usage:
        vad = VoiceActivityDetector()
        
        for audio_chunk in stream:
            if vad.is_speech(audio_chunk):
                print("User is speaking!")
    """
    
    def __init__(self, config: VADConfig = None):
        self.config = config or VADConfig()
        
        # Load Silero VAD model
        print("Loading Silero VAD model...")
        try:
            self.model, self.utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True
            )
            print("✅ Silero VAD loaded")
        except Exception as e:
            print(f"⚠️ Failed to load Silero VAD: {e}")
            print("   Using fallback energy-based detection")
            self.model = None
        
        # State tracking
        self._speech_start_ms: Optional[int] = None
        self._silence_start_ms: Optional[int] = None
        self._is_speaking = False
        self._frame_count = 0
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Check if audio chunk contains speech.
        
        Args:
            audio_chunk: Raw audio bytes (16-bit PCM)
            
        Returns:
            bool: True if speech detected, False otherwise
        """
        if self.model is None:
            # Fallback: energy-based detection
            return self._energy_based_detection(audio_chunk)
        
        # Convert bytes to tensor
        audio_int16 = np.frombuffer(audio_chunk, np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float32)
        
        # Get speech probability
        with torch.no_grad():
            speech_prob = self.model(audio_tensor, self.config.sample_rate).item()
        
        return speech_prob > self.config.threshold
    
    def _energy_based_detection(self, audio_chunk: bytes) -> bool:
        """Fallback energy-based VAD"""
        audio_int16 = np.frombuffer(audio_chunk, np.int16)
        energy = np.sqrt(np.mean(audio_int16 ** 2))
        
        # Threshold: ~500 for normal speech
        return energy > 300
    
    def process_stream(
        self,
        audio_chunk: bytes
    ) -> Tuple[bool, Optional[str]]:
        """
        Process streaming audio and track speech/silence events.
        
        Args:
            audio_chunk: Raw audio bytes
            
        Returns:
            Tuple of (is_speech, event)
            event can be: "speech_start", "speech_end", "speaking", "silence"
        """
        self._frame_count += 1
        current_ms = self._frame_count * (len(audio_chunk) // 2) * 1000 // self.config.sample_rate
        
        is_speech = self.is_speech(audio_chunk)
        event = None
        
        if is_speech:
            # Speech detected
            if not self._is_speaking:
                # Start of speech
                self._speech_start_ms = current_ms
                self._is_speaking = True
                event = "speech_start"
            else:
                event = "speaking"
            
            self._silence_start_ms = None
            
        else:
            # Silence detected
            if self._is_speaking:
                # Potential end of speech
                if self._silence_start_ms is None:
                    self._silence_start_ms = current_ms
                
                # Check if silence duration exceeded threshold
                silence_duration = current_ms - self._silence_start_ms
                if silence_duration >= self.config.min_silence_duration_ms:
                    # End of speech
                    self._is_speaking = False
                    event = "speech_end"
            else:
                event = "silence"
        
        return is_speech, event
    
    def get_speech_timestamps(
        self,
        audio: bytes,
        return_seconds: bool = False
    ) -> List[dict]:
        """
        Get precise timestamps of all speech segments in audio.
        
        Args:
            audio: Complete audio bytes
            return_seconds: If True, return timestamps in seconds, else ms
            
        Returns:
            List of dicts with 'start' and 'end' keys
        """
        if self.model is None:
            return []
        
        # Convert to float32
        audio_int16 = np.frombuffer(audio, np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float32)
        
        # Use Silero's timestamp function
        get_speech_timestamps = self.utils[0]
        
        timestamps = get_speech_timestamps(
            audio_tensor,
            self.model,
            sampling_rate=self.config.sample_rate,
            threshold=self.config.threshold,
            min_speech_duration_ms=self.config.min_speech_duration_ms,
            min_silence_duration_ms=self.config.min_silence_duration_ms,
            return_seconds=return_seconds
        )
        
        return timestamps
    
    def reset(self):
        """Reset state"""
        self._speech_start_ms = None
        self._silence_start_ms = None
        self._is_speaking = False
        self._frame_count = 0
