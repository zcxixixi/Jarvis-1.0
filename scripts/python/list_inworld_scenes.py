import requests
import asyncio
from rich.console import Console
import os

# User Credentials
API_KEY = "60KybLTCb22XiK2wFEjvgkiX8uq2XngM"
# Secret is not needed for Basic Auth if we use the header trick or requests auth
API_SECRET = "Nu9qRr0zObUfEQXdPXpxuFgvNvdzDmRJ3TKWNq4w6n8Q4Oyjf2ny4gndKEN2PPCb"
WORKSPACE_ID = "default-e2a5hut59a5mt01-w-i3rw"
AUTH_BASE64 = "NjBLeWJMVENiMjJYaUsyd0ZFanZna2lYOHVxMlhuZ006TnU5cVJyMHpPYlVmRVFYZFBYcHh1Rmd2TnZkekRtUkozVEtXTnE0dzZuOFE0T3lqZjJueTRnbmRLRU4yUFBDYg=="

console = Console()

async def list_scenes():
    console.print("🔍 Connecting to Inworld to list scenes...", style="yellow")
    
    workspace_name = f"workspaces/{WORKSPACE_ID}"
    url = f"https://api.inworld.ai/studio/v1/{workspace_name}/scenes"
    
    headers = {
        "Authorization": f"Basic {AUTH_BASE64}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            scenes = response.json().get('scenes', [])
            if not scenes:
                console.print("❌ No scenes found. Please create a Scene in the Studio first!", style="red")
                return
                
            console.print(f"✅ Found {len(scenes)} scenes:", style="green")
            for scene in scenes:
                name = scene.get('name') 
                alias = scene.get('displayName', 'No Name')
                console.print(f"- [bold cyan]{alias}[/]: {name}")
                
            first_scene = scenes[0]['name']
            console.print(f"\n🚀 Recommended Scene ID: [bold green]{first_scene}[/]")
            
        else:
             console.print(f"❌ API Error: {response.status_code} - {response.text}", style="red")

    except Exception as e:
        console.print(f"Error: {e}", style="red")

if __name__ == "__main__":
    asyncio.run(list_scenes())
