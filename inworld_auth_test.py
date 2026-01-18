
import requests
import json
import base64
import time
import hmac
import hashlib

# User Credentials
API_KEY = "60KybLTCb22XiK2wFEjvgkiX8uq2XngM"
API_SECRET = "Nu9qRr0zObUfEQXdPXpxuFgvNvdzDmRJ3TKWNq4w6n8Q4Oyjf2ny4gndKEN2PPCb"
WORKSPACE_ID = "default-e2a5hut59a5mt01-w-i3rw"

def generate_signature(secret, body, timestamp):
    message = f"{timestamp}{body}"
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def test_auth():
    print("🔐 Testing Inworld Auth...")

    # Method 1: Generate Custom Token using correct signature
    # Endpoint: https://api.inworld.ai/v1/workspaces/{workspace_id}/sessions (Start Session)
    # But we need a SCENE ID to start a session.
    
    # Let's try to query scenes again but with Runtime API if possible, or correct signature.
    # Wait, the Studio API might require a different simpler auth if we are admin.
    
    # Official docs say: "Generate a session token"
    # POST https://api.inworld.ai/v1/generate_token
    # Config: Key/Secret in body
    
    url = "https://api.inworld.ai/v1/generate_token"
    payload = {
        "key": API_KEY,
        "secret": API_SECRET
    }
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get('token')
            print(f"✅ Token Generated: {token[:10]}...")
            return token
        else:
            print(f"❌ Token Gen Error: {response.status_code} - {response.text}")
            
            # Fallback: Try Basic Auth on token endpoint
            print("\nTrying Basic Auth fallback...")
            auth_str = f"{API_KEY}:{API_SECRET}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            
            headers = {"Authorization": f"Basic {b64_auth}"}
            # Try workspace token endpoint
            url2 = f"https://api.inworld.ai/v1/workspaces/{WORKSPACE_ID}/sessions" 
            # This needs scene, so it will fail 400 likely, but 401 means auth fail.
            
            resp2 = requests.post(url2, headers=headers, json={}) # Empty body
            print(f"Fallback Resp: {resp2.status_code} (Expect 400 if auth ok, 401 if auth bad)")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_auth()
