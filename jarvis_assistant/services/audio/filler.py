import asyncio
import random
import os
import time

class FillerPhraseManager:
    """
    Manages playback of 'filler' sounds (e.g. 'Hmm...', 'Let me check') 
    to mask latency while the Brain is thinking.
    """
    def __init__(self, resource_dir=None):
        if not resource_dir:
            # Default to assets folder in package
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            resource_dir = os.path.join(base_dir, "assets", "sounds", "fillers")
        
        self.resource_dir = resource_dir
        self.active_task = None
        self.should_stop = False
        
        # Define filler categories
        self.fillers = {
            "short": ["hmm.wav", "uh_huh.wav"], 
            "long": ["let_me_check.wav", "one_moment.wav"]
        }
        
        # Ensure dir exists
        os.makedirs(self.resource_dir, exist_ok=True)

    async def play_filler_delayed(self, delay: float = 0.8):
        """Wait for `delay` seconds, then play a random filler if not stopped."""
        self.should_stop = False
        try:
            await asyncio.sleep(delay)
            if not self.should_stop:
                await self._play_random_filler()
        except asyncio.CancelledError:
            pass

    async def _play_random_filler(self):
        """Play a sound file using local player logic."""
        # Simple placeholder player using audio_utils
        # In real app, integration with Output Audio Stream is needed.
        # But for now we can just play to speaker?
        # NO, we should ideally inject into the output stream or generic player.
        # Let's use `pyaudio` or `playsound` or helper.
        
        # For now, let's assume we print log and simulate 
        # because we don't have the actual wav files yet.
        print("🤔 [Filler] Playing 'Hmm...' sound...")
        
        # If we had files:
        # from jarvis_assistant.utils.audio_utils import play_wav
        # play_wav("hmm.wav") 
        pass

    def start(self, delay=0.8):
        """Start the timer for filler phrase."""
        self.stop() # Cancel existing
        self.active_task = asyncio.create_task(self.play_filler_delayed(delay))

    def stop(self):
        """Cancel pending filler or stop playing."""
        self.should_stop = True
        if self.active_task:
            self.active_task.cancel()
            self.active_task = None
