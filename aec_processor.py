"""
Software AEC (Acoustic Echo Cancellation) Module
Uses pyaec (SpeexDSP-based) to cancel speaker echo from microphone input
"""

import struct
import collections
from typing import Optional


class SoftwareAEC:
    """
    Software-based Acoustic Echo Cancellation.
    
    Usage:
        aec = SoftwareAEC(sample_rate=16000, frame_size=160)
        
        # When playing audio to speaker:
        aec.feed_reference(speaker_audio_bytes)
        
        # When processing microphone input:
        clean_audio = aec.cancel_echo(mic_audio_bytes)
    """
    
    def __init__(self, sample_rate: int = 16000, frame_size: int = 160, filter_length: int = 1024):
        """
        Initialize AEC processor.
        
        Args:
            sample_rate: Audio sample rate (Hz), must match both mic and speaker
            frame_size: Number of samples per frame (e.g., 160 for 10ms at 16kHz)
            filter_length: AEC filter length in samples (longer = better for delayed echo)
        """
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.filter_length = filter_length
        self._initialized = False
        self.aec = None
        
        # Buffer for reference signal (what's being played to speaker)
        # Use a delay buffer to account for bluetooth latency (~150-300ms)
        self.bluetooth_delay_ms = 200  # Adjustable: estimated bluetooth delay
        self.delay_samples = int(sample_rate * self.bluetooth_delay_ms / 1000)
        self.reference_buffer = collections.deque(maxlen=self.delay_samples + frame_size * 10)
        
        try:
            from pyaec import Aec
            self.aec = Aec(
                frame_size=frame_size,
                filter_length=filter_length,
                sample_rate=sample_rate,
                enable_preprocess=True  # Enable noise suppression too
            )
            self._initialized = True
            
            # Pre-fill buffer with silence to account for latency
            # This aligns "Output at T" with "Input at T + Delay"
            silence_padding = [0] * self.delay_samples
            self.reference_buffer.extend(silence_padding)
            
            print(f"[AEC] ✅ Initialized: frame_size={frame_size}, filter_length={filter_length}, sample_rate={sample_rate}")
            print(f"[AEC] Bluetooth/System delay compensation: {self.bluetooth_delay_ms}ms (Buffered {self.delay_samples} silence samples)")
        except Exception as e:
            print(f"[AEC] ❌ Failed to initialize: {e}")
    
    @property
    def is_ready(self) -> bool:
        return self._initialized and self.aec is not None
    
    def feed_reference(self, speaker_audio: bytes) -> None:
        """
        Feed audio data that is being sent to speakers.
        This becomes the "far-end" reference for echo cancellation.
        
        Args:
            speaker_audio: Raw PCM audio bytes (16-bit signed, mono)
        """
        if not self.is_ready:
            return
            
        # Convert bytes to samples and add to buffer
        num_samples = len(speaker_audio) // 2
        samples = struct.unpack(f"{num_samples}h", speaker_audio)
        self.reference_buffer.extend(samples)
    
    def cancel_echo(self, mic_audio: bytes) -> bytes:
        """
        Process microphone audio and remove echo.
        
        Args:
            mic_audio: Raw PCM audio bytes from microphone (16-bit signed, mono)
            
        Returns:
            Processed audio with echo removed (same format)
        """
        if not self.is_ready:
            return mic_audio
        
        # Convert mic audio to samples
        num_samples = len(mic_audio) // 2
        if num_samples < self.frame_size:
            return mic_audio
            
        mic_samples = list(struct.unpack(f"{num_samples}h", mic_audio))
        
        # Get delayed reference signal
        if len(self.reference_buffer) < self.frame_size:
            # Not enough reference data yet, return original
            return mic_audio
        
        # Extract reference samples (with delay compensation)
        ref_samples = []
        for _ in range(min(self.frame_size, len(self.reference_buffer))):
            if self.reference_buffer:
                ref_samples.append(self.reference_buffer.popleft())
            else:
                ref_samples.append(0)
        
        # Pad if needed
        while len(ref_samples) < self.frame_size:
            ref_samples.append(0)
        
        # Process through AEC
        try:
            # cancel_echo(rec_buffer, echo_buffer) -> processed
            clean_samples = self.aec.cancel_echo(
                mic_samples[:self.frame_size],
                ref_samples
            )
            
            # Convert back to bytes
            return struct.pack(f"{len(clean_samples)}h", *clean_samples)
        except Exception as e:
            # On error, return original
            return mic_audio
    
    def set_bluetooth_delay(self, delay_ms: int) -> None:
        """
        Adjust the bluetooth delay compensation.
        
        Args:
            delay_ms: Estimated delay in milliseconds (typical: 100-300ms)
        """
        self.bluetooth_delay_ms = delay_ms
        self.delay_samples = int(self.sample_rate * delay_ms / 1000)
        print(f"[AEC] Bluetooth delay updated: {delay_ms}ms ({self.delay_samples} samples)")
    
    def reset(self) -> None:
        """Reset the reference buffer and AEC state."""
        self.reference_buffer.clear()
        print("[AEC] Reset complete")


# Singleton instance for easy access
_aec_instance: Optional[SoftwareAEC] = None


def get_aec(sample_rate: int = 16000, frame_size: int = 160) -> SoftwareAEC:
    """Get or create singleton AEC instance."""
    global _aec_instance
    if _aec_instance is None:
        _aec_instance = SoftwareAEC(sample_rate=sample_rate, frame_size=frame_size)
    return _aec_instance
