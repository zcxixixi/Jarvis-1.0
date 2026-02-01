"""
Audio I/O Module - Handles microphone and speaker
Clean wrapper around PyAudio with async support

This replaces ~400 lines from hybrid_jarvis.py
"""

import pyaudio
import asyncio
import threading
import queue
from typing import AsyncGenerator, Optional
from dataclasses import dataclass
import numpy as np

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import AudioConfig

class AudioIO:
    """
    Manages audio input/output using PyAudio.
    Provides async interface for easy integration.
    
    Features:
    - Async read/write
    - Thread-safe queues
    - Automatic device discovery
    - Echo cancellation ready
    
    Usage:
        audio = AudioIO(config)
        await audio.start()
        
        # Read from mic
        async for chunk in audio.read_stream():
            process(chunk)
        
        # Write to speaker
        await audio.write(audio_data)
        
        await audio.stop()
    """
    
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig()
        self.pyaudio_instance = pyaudio.PyAudio()
        
        # Streams
        self._mic_stream: Optional[pyaudio.Stream] = None
        self._speaker_stream: Optional[pyaudio.Stream] = None
        
        # State
        self._is_running = False
        self._mic_thread: Optional[threading.Thread] = None
        self._speaker_thread: Optional[threading.Thread] = None
        
        # Queues (thread-safe)
        self._mic_queue = queue.Queue(maxsize=100)
        self._speaker_queue = queue.Queue(maxsize=100)
        
        # Async event loop
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def _find_device_by_name(self, name: str, is_input: bool) -> Optional[int]:
        """Find audio device index by name"""
        info = self.pyaudio_instance.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        for i in range(num_devices):
            device_info = self.pyaudio_instance.get_device_info_by_host_api_device_index(0, i)
            
            # Check if device matches criteria
            max_channels = device_info.get('maxInputChannels') if is_input else device_info.get('maxOutputChannels')
            if max_channels > 0 and name.lower() in device_info.get('name', '').lower():
                return device_info.get('index')
        
        return None
    
    async def start(self):
        """Initialize audio streams and start reading"""
        if self._is_running:
            print("⚠️ AudioIO already running")
            return
        
        self._is_running = True
        self._loop = asyncio.get_event_loop()
        
        # Find device if name specified
        mic_device = None
        if self.config.device_name:
            mic_device = self._find_device_by_name(self.config.device_name, is_input=True)
            if mic_device is not None:
                print(f"🎤 Using microphone: {self.config.device_name} (index {mic_device})")
            else:
                print(f"⚠️ Device '{self.config.device_name}' not found, using default")
        
        # Open microphone stream
        try:
            self._mic_stream = self.pyaudio_instance.open(
                rate=self.config.sample_rate,
                channels=self.config.channels,
                format=pyaudio.paInt16,
                input=True,
                input_device_index=mic_device,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._mic_callback
            )
            print(f"✅ Microphone opened: {self.config.sample_rate}Hz, {self.config.chunk_size} frames")
        except Exception as e:
            print(f"❌ Failed to open microphone: {e}")
            raise
        
        # Open speaker stream
        try:
            self._speaker_stream = self.pyaudio_instance.open(
                rate=self.config.sample_rate,
                channels=self.config.speaker_channels,
                format=pyaudio.paInt16,
                output=True,
                frames_per_buffer=self.config.chunk_size,
            )
            print(f"✅ Speaker opened: {self.config.sample_rate}Hz, {self.config.speaker_channels} channels")
        except Exception as e:
            print(f"❌ Failed to open speaker: {e}")
            raise
        
        # Start speaker worker thread
        self._speaker_thread = threading.Thread(target=self._speaker_worker, daemon=True)
        self._speaker_thread.start()
        
        print("🔊 AudioIO started successfully")
    
    def _mic_callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio callback for microphone input.
        Runs in separate thread managed by PyAudio.
        """
        if status:
            print(f"⚠️ Mic status: {status}")
        
        try:
            self._mic_queue.put_nowait(in_data)
        except queue.Full:
            # Drop frame if queue is full (prevents blocking)
            pass
        
        return (None, pyaudio.paContinue)
    
    async def read_stream(self) -> AsyncGenerator[bytes, None]:
        """
        Async generator that yields microphone audio chunks.
        
        Yields:
            bytes: Raw audio data (16-bit PCM)
        """
        while self._is_running:
            try:
                # Non-blocking check with timeout
                chunk = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self._mic_queue.get,
                    True,  # block
                    0.1    # timeout
                )
                yield chunk
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue
    
    async def write(self, audio_data: bytes):
        """
        Write audio data to speaker queue.
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM)
        """
        if not self._is_running:
            print("⚠️ AudioIO not running, cannot write")
            return
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._speaker_queue.put,
                audio_data,
                True,  # block
                1.0    # timeout
            )
        except queue.Full:
            print("⚠️ Speaker queue full, dropping audio")
    
    def _speaker_worker(self):
        """
        Worker thread that reads from speaker queue and plays audio.
        Runs in separate thread to avoid blocking.
        """
        print("🧵 Speaker worker started")
        
        while self._is_running:
            try:
                # Get audio data from queue
                data = self._speaker_queue.get(timeout=0.1)
                
                # Write to speaker
                if self._speaker_stream:
                    self._speaker_stream.write(data)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Speaker worker error: {e}")
        
        print("🧵 Speaker worker stopped")
    
    def clear_speaker_queue(self):
        """Clear all pending audio from speaker queue"""
        count = 0
        while not self._speaker_queue.empty():
            try:
                self._speaker_queue.get_nowait()
                count += 1
            except queue.Empty:
                break
        
        if count > 0:
            print(f"🔇 Cleared {count} chunks from speaker queue")
    
    async def stop(self):
        """Stop all audio streams and cleanup"""
        print("🛑 Stopping AudioIO...")
        self._is_running = False
        
        # Stop streams
        if self._mic_stream:
            self._mic_stream.stop_stream()
            self._mic_stream.close()
            self._mic_stream = None
        
        if self._speaker_stream:
            self._speaker_stream.stop_stream()
            self._speaker_stream.close()
            self._speaker_stream = None
        
        # Wait for threads
        if self._speaker_thread and self._speaker_thread.is_alive():
            self._speaker_thread.join(timeout=2.0)
        
        # Terminate PyAudio
        self.pyaudio_instance.terminate()
        
        print("✅ AudioIO stopped")
    
    def get_volume_level(self, audio_chunk: bytes) -> float:
        """
        Calculate volume level of audio chunk (0.0 - 1.0).
        Useful for debugging and visualization.
        
        Args:
            audio_chunk: Raw audio bytes
            
        Returns:
            float: Volume level (0.0 = silence, 1.0 = max)
        """
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
        rms = np.sqrt(np.mean(audio_int16 ** 2))
        max_amplitude = 32768.0  # Max for int16
        return min(rms / max_amplitude, 1.0)
