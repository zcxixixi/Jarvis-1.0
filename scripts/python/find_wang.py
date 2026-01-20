
from cartesia import Cartesia

API_KEY = "sk_car_f5k7zJEV3AiNorLHgio9M9"
client = Cartesia(api_key=API_KEY)

target_names = ["Wang - Guide", "Hao - Friendly Guy"]

print("🔍 Searching for specific voices...")
try:
    voices = client.voices.list()
    found = False
    for v in voices:
        if v.name in target_names:
            print(f"✅ FOUND: {v.name}")
            print(f"   ID: {v.id}")
            print(f"   Desc: {v.description}")
            found = True
            
    if not found:
        print("❌ Could not find exact matches. Listing all 'Chinese-like' names:")
        for v in voices:
            if any(n in v.name for n in ["Wang", "Hao", "Li", "Zhang", "Chen", "Liu"]):
                print(f"   - {v.name}: {v.id}")

except Exception as e:
    print(f"Error: {e}")
