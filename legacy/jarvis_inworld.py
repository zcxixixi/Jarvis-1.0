import asyncio
import os
from inworld.client import InworldClient
from inworld.client.common import auth
from inworld.entities import InworldSession
from rich.console import Console

# User Credentials
API_KEY = "60KybLTCb22XiK2wFEjvgkiX8uq2XngM"
API_SECRET = "Nu9qRr0zObUfEQXdPXpxuFgvNvdzDmRJ3TKWNq4w6n8Q4Oyjf2ny4gndKEN2PPCb"
WORKSPACE_ID = "default-e2a5hut59a5mt01-w-i3rw"
# We need a character name too, usually constructed from workspace.
# Assuming a default character exists or we list them.
# For now let's try to list characters to pick one, or use a default if SDK allows.

console = Console()

async def interactive_session():
    console.print("🤖 Connecting to Inworld AI...", style="yellow")
    
    client = InworldClient()
    # Authenticate
    # Note: The SDK usage might detailed configuration. 
    # Based on general SDK patterns:
    
    # We need to set environment variables or pass config
    os.environ["INWORLD_ACCESS_KEY"] = API_KEY
    os.environ["INWORLD_SECRET_KEY"] = API_SECRET
    
    # Simple loop for text input -> Audio output
    # Since we don't have the exact scene/character ID yet, 
    # we might need to query it or the user might run a 'setup' step.
    
    # Let's create a logical wrapper that uses Groq for brain (as user wants custom brain) 
    # AND Inworld for Voice?
    # Actually Inworld is a "Character Platform", it usually provides BOTH brain and voice.
    # If user wants JARVIS brain (Groq + Custom Prompt) but Inworld Voice:
    # We need to use Inworld's "Send Text" API just to trigger the TTS? 
    # But Inworld characters reply with their own AI.
    
    # Wait, if user wants "Jarvis", usually implies the LLM behavior too.
    # If we use Inworld, we are using Inworld's Brain + Voice.
    # That might be better for latency!
    
    console.print("✅ Inworld SDK Installed!", style="green")
    console.print("⚠️ To run a session, we need a SCENE ID or CHARACTER ID.", style="bold red")
    console.print(f"Workspace: {WORKSPACE_ID}")
    
    # We will try to fetch scenes
    # But for now, let's just confirm installation and readiness
    
if __name__ == "__main__":
    asyncio.run(interactive_session())
