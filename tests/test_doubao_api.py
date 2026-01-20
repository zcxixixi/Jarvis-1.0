
import asyncio
import uuid
import json
import gzip
import sys
import protocol
import websockets
import jarvis_doubao_config as config

async def test_doubao_api():
    print("☁️  Doubao Cloud API Test")
    print("-------------------------")
    
    session_id = str(uuid.uuid4())
    pass_criteria = {"connected": False, "session_started": False, "response_received": False}
    
    try:
        headers = config.ws_connect_config["headers"]
        base_url = config.ws_connect_config["base_url"]
        
        print(f"1. Connecting to {base_url}...")
        # SSL Context
        import ssl
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        async with websockets.connect(base_url, additional_headers=headers, ssl=ssl_ctx) as ws:
            pass_criteria["connected"] = True
            print("   ✅ Connected.")
            
            # --- 1. StartConnection ---
            req = bytearray(protocol.generate_header())
            req.extend((1).to_bytes(4, 'big'))
            payload = gzip.compress(b"{}")
            req.extend(len(payload).to_bytes(4, 'big'))
            req.extend(payload)
            await ws.send(req)
            resp = await ws.recv()
            print("   ✅ StartConnection Handshake OK.")
            
            # --- 2. StartSession ---
            req_params = config.start_session_req
            payload = gzip.compress(json.dumps(req_params).encode('utf-8'))
            req = bytearray(protocol.generate_header())
            req.extend((100).to_bytes(4, 'big'))
            req.extend(len(session_id).to_bytes(4, 'big'))
            req.extend(session_id.encode('utf-8'))
            req.extend(len(payload).to_bytes(4, 'big'))
            req.extend(payload)
            await ws.send(req)
            resp = await ws.recv()
            
            parsed = protocol.parse_response(resp)
            if parsed.get('message_type') in ['SERVER_FULL_RESPONSE', 'SERVER_ACK']:
                 pass_criteria["session_started"] = True
                 print("   ✅ Session Started.")
            else:
                 print(f"   ⚠️ Session Start Response Warning: {parsed}")
            
            # --- 3. Send Text Query "Testing" ---
            query_text = "你好，这是一次连接测试。"
            print(f"2. Sending Text Query: '{query_text}'...")
            payload = {"content": query_text}
            payload_bytes = gzip.compress(json.dumps(payload).encode('utf-8'))
            req = bytearray(protocol.generate_header(
                message_type=protocol.CLIENT_FULL_REQUEST,
                serial_method=protocol.JSON
            ))
            req.extend((501).to_bytes(4, 'big'))
            req.extend(len(session_id).to_bytes(4, 'big'))
            req.extend(session_id.encode('utf-8'))
            req.extend(len(payload_bytes).to_bytes(4, 'big'))
            req.extend(payload_bytes)
            await ws.send(req)
            
            # --- 4. Verify Response ---
            print("3. Waiting for Audio/Text Response (Timeout 5s)...")
            try:
                while True:
                    resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    parsed = protocol.parse_response(resp)
                    
                    if 'payload_msg' in parsed:
                        msg = parsed['payload_msg']
                        
                        # Check for Audio
                        if isinstance(msg, bytes) and len(msg) > 0:
                            if not pass_criteria["response_received"]:
                                print("   ✅ Audio Stream Received.")
                                pass_criteria["response_received"] = True
                                return True # Success! We heard back.
                        
                        # Check for Text
                        elif isinstance(msg, dict):
                            txt = msg.get('text') or msg.get('content')
                            if txt:
                                print(f"   🗣️  Jarvis says: {txt}")
                                
            except asyncio.TimeoutError:
                print("   ⚠️ Timeout waiting for response.")
                
    except Exception as e:
        print(f"\n❌ Test Failed with Exception: {e}")
        return False
        
    return pass_criteria["response_received"]

if __name__ == "__main__":
    success = asyncio.run(test_doubao_api())
    if success:
        print("\n🎉 API TEST PASSED: Cloud connection is healthy.")
        sys.exit(0)
    else:
        print("\n💥 API TEST FAILED: Could not complete conversation.")
        sys.exit(1)
