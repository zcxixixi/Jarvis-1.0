
import asyncio
import uuid
import json
import gzip
import protocol
import websockets
import jarvis_doubao_config as config

async def test_minimal():
    session_id = str(uuid.uuid4())
    print(f"Testing Session: {session_id}")
    
    headers = config.ws_connect_config["headers"]
    base_url = config.ws_connect_config["base_url"]
    
    async with websockets.connect(base_url, additional_headers=headers) as ws:
        # 1. StartConnection
        req = bytearray(protocol.generate_header())
        req.extend((1).to_bytes(4, 'big'))
        payload = gzip.compress(b"{}")
        req.extend(len(payload).to_bytes(4, 'big'))
        req.extend(payload)
        await ws.send(req)
        resp = await ws.recv()
        print("StartConnection ACK received.")
        
        # 2. StartSession
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
        print(f"StartSession Response: {protocol.parse_response(resp)}")
        
        # 3. Send Text Query "你好"
        print("Sending '你好'...")
        payload = {"content": "你好"}
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
        
        # 4. Listen for 5 seconds
        print("Listening for responses for 5 seconds...")
        try:
            while True:
                resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
                parsed = protocol.parse_response(resp)
                if 'payload_msg' in parsed:
                    msg = parsed['payload_msg']
                    if isinstance(msg, dict):
                        print(f"Event: {msg.get('type')} - {msg.get('text') or msg.get('transcript') or msg}")
                    else:
                        print("Audio bytes received.")
        except asyncio.TimeoutError:
            print("Test finished (No more data).")

if __name__ == "__main__":
    asyncio.run(test_minimal())
