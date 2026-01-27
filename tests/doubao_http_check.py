import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DOUBAO_ARK_API_KEY") # Updated
endpoint_id = os.getenv("DOUBAO_ENDPOINT_ID")

if __name__ == "__main__":
    print("🔑 Testing Doubao Integration")
    print(f"   Model: {endpoint_id}")
    safe_token = f"{api_key[:5]}...{api_key[-5:]}" if api_key else "None"
    print(f"   Token: {safe_token}")

    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" 
    }
    payload = {
        "model": endpoint_id,
        "messages": [
            {"role": "user", "content": "Hello Jarvis, are you ready?"}
        ]
    }

    try:
        print("📡 Sending Request...")
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"📥 Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"✅ Response: {resp.json()['choices'][0]['message']['content']}")
            exit(0)
        else:
            print(f"❌ Error: {resp.text}")
            exit(1)
    except Exception as e:
        print(f"❌ Exception: {e}")
        exit(1)
