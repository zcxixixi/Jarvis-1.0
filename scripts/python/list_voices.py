
from cartesia import Cartesia
from rich.console import Console
from rich.table import Table

console = Console()
API_KEY = "sk_car_f5k7zJEV3AiNorLHgio9M9"
client = Cartesia(api_key=API_KEY)

def list_voices():
    console.print("🔍 Fetching Voice Library...", style="yellow")
    try:
        voices = client.voices.list()
        
        table = Table(title="Cartesia Available Voices")
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Gender", style="green")
        table.add_column("Description")
        
        # Sort or filter?
        # Let's print all to see metadata structure
        count = 0
        for v in voices:
            # Check if dict or object
            # SDK 2.0 returns objects usually
            name = getattr(v, "name", "N/A")
            vid = getattr(v, "id", "N/A")
            # Attributes might differ. Look for language support indicators if any.
            meta = getattr(v, "description", "") or ""
            
            # Simple gender heuristic from description or name
            gender = "Unknown"
            if "Female" in str(v) or "Female" in meta: gender = "Female"
            elif "Male" in str(v) or "Male" in meta: gender = "Male"
            
            # Print only reasonable number or filtered
            # We want CHINESE or MULTILINGUAL
            # But Cartesia voices are often model-agnostic?
            # Sonic Multilingual can use ANY voice, but natives sound better.
            
            # Let's just dump the top 20 or ones with "Chinese" in name/desc
            table.add_row(name, vid, gender, str(meta)[:50])
            count += 1
            
        console.print(table)
        console.print(f"Total Voices: {count}")
        
    except Exception as e:
        console.print(f"Error: {e}", style="red")
        # Try inspecting raw list if object access fails
        pass

if __name__ == "__main__":
    list_voices()
