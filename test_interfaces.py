#!/usr/bin/env python3
"""
Test clean interfaces with console I/O.
Validates interface design before building agent.
"""

import asyncio
from jarvis_assistant.io.text import ConsoleInput, ConsoleOutput


async def test_console_io():
    """Test console input/output interfaces."""
    print("🧪 Testing Clean Interfaces")
    print("=" * 60)
    
    # Create I/O handlers
    input_handler = ConsoleInput(prompt="You: ")
    output_handler = ConsoleOutput(prefix="Assistant: ")
    
    # Test basic flow
    print("\n📝 Type something and press Enter (or 'quit' to exit)\n")
    
    while True:
        # Listen for input
        user_text = await input_handler.listen()
        
        if user_text.lower() in ["quit", "exit", "bye"]:
            await output_handler.speak("Goodbye! 👋")
            break
        
        # Echo back (agent placeholder)
        response = f"You said: '{user_text}' (length: {len(user_text)} chars)"
        await output_handler.speak(response)
    
    print("\n✅ Interface test complete!")


async def test_streaming():
    """Test streaming output."""
    print("\n🧪 Testing Streaming Output")
    print("=" * 60)
    
    output_handler = ConsoleOutput(prefix="Streaming: ")
    
    # Simulate streaming response
    async def generate_chunks():
        chunks = ["Hello", " ", "from", " ", "streaming", " ", "output!"]
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.2)  # Simulate generation delay
    
    await output_handler.speak_stream(generate_chunks())
    print("\n✅ Streaming test complete!")


if __name__ == "__main__":
    print("🚀 Clean Interface Test Suite\n")
    
    # Run tests
    asyncio.run(test_console_io())
    # asyncio.run(test_streaming())  # Uncomment to test streaming
