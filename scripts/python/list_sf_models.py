
import requests
from rich.console import Console

console = Console()
API_KEY = "1502cbac-76d5-49d6-8952-5a75f6f633b4"
BASE_URL = "https://api.siliconflow.cn/v1/models"

def list_sf_models():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(BASE_URL, headers=headers)
        if response.status_code == 200:
            models = response.json().get("data", [])
            console.print(f"Found {len(models)} models. Filtering for 'audio' or 'tts'...", style="green")
            
            for m in models:
                mid = m.get("id", "")
                # Filtering logic
                if "tts" in mid.lower() or "audio" in mid.lower() or "doubao" in mid.lower() or "voice" in mid.lower():
                    console.print(f"🎤 {mid}")
        else:
            console.print(f"Error: {response.status_code} - {response.text}", style="red")
            
    except Exception as e:
        console.print(f"Error: {e}", style="red")

if __name__ == "__main__":
    list_sf_models()
