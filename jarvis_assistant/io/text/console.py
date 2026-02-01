"""
Console I/O implementations for testing.
Allows testing agent without ASR/TTS hardware.
"""

import asyncio
from typing import AsyncIterator
from jarvis_assistant.interfaces import InputInterface, OutputInterface


class ConsoleInput(InputInterface):
    """
    Console input implementation.
    Reads text from terminal for testing.
    """
    
    def __init__(self, prompt: str = "> "):
        self.prompt = prompt
    
    async def listen(self) -> str:
        """Read line from console."""
        # Run input() in thread to avoid blocking event loop
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, input, self.prompt)
        return text.strip()
    
    async def listen_stream(self) -> AsyncIterator[str]:
        """Yield complete line (no streaming for console)."""
        text = await self.listen()
        yield text
    
    async def wait_for_wake_word(self) -> bool:
        """No wake word for console, always ready."""
        return True


class ConsoleOutput(OutputInterface):
    """
    Console output implementation.
    Prints text to terminal for testing.
    Demonstrates streaming pattern for DoubaoTTS to follow.
    """
    
    def __init__(self, prefix: str = "Jarvis: ", enable_streaming_demo: bool = True):
        self.prefix = prefix
        self.enable_streaming_demo = enable_streaming_demo
    
    async def speak(self, text: str):
        """Print text to console."""
        print(f"{self.prefix}{text}")
    
    async def speak_stream(self, text_stream: AsyncIterator[str]):
        """
        Stream text chunks as they arrive (demonstrates streaming pattern).
        
        This shows how DoubaoTTS should implement streaming:
        1. Start playing audio ASAP
        2. Continue synthesizing chunks in parallel
        3. Minimize gaps between chunks
        """
        print(self.prefix, end="", flush=True)
        
        chunk_count = 0
        async for chunk in text_stream:
            chunk_count += 1
            
            if self.enable_streaming_demo and chunk_count == 1:
                # First chunk - simulate instant feedback
                print(f"[{chunk}]", end="", flush=True)
            else:
                print(chunk, end="", flush=True)
            
            # Simulate small synthesis delay (realistic)
            await asyncio.sleep(0.05)  # 50ms per chunk
        
        print()  # Newline at end
    
    async def play_acknowledgment(self):
        """
        Instant feedback demo.
        Real TTS would play cached audio file (<50ms).
        """
        print("🎵 *beep* ", end="", flush=True)  # Instant (~1ms)
        await asyncio.sleep(0.05)  # Simulate 50ms audio playback
    
    async def show_thinking(self, message: str):
        """Show status message."""
        print(f"💭 {message}")
