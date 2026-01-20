import requests
import base64
import json

# User Credentials
API_KEY = "60KybLTCb22XiK2wFEjvgkiX8uq2XngM"
API_SECRET = "Nu9qRr0zObUfEQXdPXpxuFgvNvdzDmRJ3TKWNq4w6n8Q4Oyjf2ny4gndKEN2PPCb"
WORKSPACE_ID = "default-e2a5hut59a5mt01-w-i3rw"

def get_access_token():
    url = "https://api.inworld.ai/v1/auth/token"
    # Basic Auth with Key:Secret
    # But Inworld often uses custom signature. Let's try standard client_credentials if supported
    # Actually Inworld documentation says: use Key/Secret to sign requests OR exchange for token.
    
    # Modern Inworld API uses a strict HMAC signature, which is complex to implement from scratch without SDK.
    # Let's try the simple token exchange if it exists.
    
    # Actually, let's try to install the SDK from a more specific source if possible, or use a simpler alternative if Inworld turns out to be too complex without SDK.
    # But wait! I recall there is no official 'pip install inworld' that is widely maintained.
    
    pass

if __name__ == "__main__":
    print("Inworld SDK not found on PyPI. Checking alternatives...")
