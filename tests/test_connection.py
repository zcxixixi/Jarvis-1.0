
import asyncio
import websockets
import ssl
import json
import uuid
import gzip
import os
from dotenv import load_dotenv

# Load .env manually to be sure
load_dotenv()

APP_ID = os.getenv("DOUBAO_APP_ID")
ACCESS_TOKEN = os.getenv("DOUBAO_ACCESS_TOKEN")

print(f"🔧 Config Check:")
print(f"   APP_ID: {APP_ID}")
print(f"   TOKEN:  {ACCESS_TOKEN[:6] if ACCESS_TOKEN else 'None'}......")

WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"

async def test_connect():
    headers = {
        "X-Api-App-ID": APP_ID,
        "X-Api-Access-Key": ACCESS_TOKEN,
        "X-Api-Resource-Id": "volc.speech.dialog",
        "X-Api-App-Key": "PlgvMymc7f3tQnJ6",
        "X-Api-Connect-Id": str(uuid.uuid4())
    }

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    print(f"\n🚀 Connecting to {WS_URL}...")
    try:
        async with websockets.connect(WS_URL, additional_headers=headers, ssl=ssl_ctx) as ws:
            print("✅ WebSocket Connection Established!")
            print(f"   Remote Address: {ws.remote_address}")
            
            # Send minimal StartConnection
            import protocol # Assuming correct protocol.py exists
            req = bytearray(protocol.generate_header(message_type=1)) # CLIENT_FULL_REQUEST
            req.extend((1).to_bytes(4, 'big')) # StartConnection Event
            payload = gzip.compress(json.dumps({}).encode('utf-8'))
            req.extend(len(payload).to_bytes(4, 'big'))
            req.extend(payload)
            
            await ws.send(req)
            print("📤 Sent StartConnection...")
            
            resp = await ws.recv()
            print(f"📥 Received Response (Len: {len(resp)})")
            
            # Simple parse check
            parsed = protocol.parse_response(resp)
            print("✅ Protocol Parse Success.")
            print(f"   Response Payload: {parsed.get('payload_msg')}")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n❌ Connection Failed with HTTP Status: {e.status_code}")
        print("   -> 401: Invalid Token/AppID")
        print("   -> 403: No Permission")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    if not APP_ID or not ACCESS_TOKEN:
        print("❌ Error: Missing credentials in .env")
        exit(1)
    
    # Ensure protocol.py is importable
    import sys
    sys.path.append(os.getcwd())
    
    try:
        asyncio.run(test_connect())
    except KeyboardInterrupt:
        pass
