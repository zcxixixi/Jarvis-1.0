#!/usr/bin/env python3
"""
Test new LangGraph agent with console I/O.
No ASR/TTS needed - pure text testing.
"""

import asyncio
from jarvis_assistant.agent import JarvisAgent
from jarvis_assistant.io.text import ConsoleInput, ConsoleOutput


async def test_langgraph_agent():
    """Test agent end-to-end with console I/O."""
    print("🧪 Testing LangGraph Agent")
    print("=" * 60)
    
    # Create agent (pure, no I/O knowledge)
    agent = JarvisAgent(session_id="test_session")
    
    # Create I/O handlers
    input_handler = ConsoleInput(prompt="You: ")
    output_handler = ConsoleOutput(prefix="Jarvis: ")
    
    print("\n💬 Chat with Jarvis (type 'quit' to exit)\n")
    
    while True:
        # Get input
        user_text = await input_handler.listen()
        
        if user_text.lower() in ["quit", "exit", "bye"]:
            await output_handler.speak("Goodbye! 👋")
            break
        
        # Process with agent
        response = await agent.process(user_text)
        
        # Output response
        await output_handler.speak(response)
    
    print("\n✅ Agent test complete!")


if __name__ == "__main__":
    asyncio.run(test_langgraph_agent())
