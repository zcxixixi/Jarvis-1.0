
import asyncio
import uuid
import json
import gzip
import protocol
import websockets
import jarvis_doubao_config as config
import numpy as np

async def probe_audio():
    session_id = str(uuid.uuid4())
    print(f"Probing Session: {session_id}")
    
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
        await ws.recv()
        
        # 2. StartSession (Request pcm_s16le)
        req_params = config.start_session_req.copy()
        req_params["tts"]["audio_config"]["format"] = "pcm_s16le"
        payload = gzip.compress(json.dumps(req_params).encode('utf-8'))
        req = bytearray(protocol.generate_header())
        req.extend((100).to_bytes(4, 'big'))
        req.extend(len(session_id).to_bytes(4, 'big'))
        req.extend(session_id.encode('utf-8'))
        req.extend(len(payload).to_bytes(4, 'big'))
        req.extend(payload)
        await ws.send(req)
        await ws.recv()
        
        # 3. Request short text
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
        
        print("Capturing audio samples...")
        captured_data = b""
        try:
            while len(captured_data) < 10000:
                resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
                parsed = protocol.parse_response(resp)
                msg = parsed.get('payload_msg')
                if isinstance(msg, bytes):
                    captured_data += msg
                    print(f"Got {len(msg)} bytes")
        except:
            pass
            
        if captured_data:
            print(f"Total bytes captured: {len(captured_data)}")
            # Heuristic check
            # If Int16, max values should be within reasonable range.
            # If Float32, values should be between -1.0 and 1.0.
            
            try:
                # Try Int16
                i16 = np.frombuffer(captured_data, dtype=np.int16)
                print(f"Int16 Analysis: Max={np.max(np.abs(i16))}, Mean={np.mean(np.abs(i16))}")
                
                # Try Float32
                f32 = np.frombuffer(captured_data, dtype=np.float32)
                f32_abs_max = np.max(np.abs(f32))
                print(f"Float32 Analysis: Max={f32_abs_max}, Mean={np.mean(np.abs(f32))}")
                
                if f32_abs_max <= 2.0:
                    print("🎯 HEURISTIC: Likely Float32")
                else:
                    print("🎯 HEURISTIC: Likely Int16")
                    
            except Exception as e:
                print(f"Analysis error: {e}")

if __name__ == "__main__":
    asyncio.run(probe_audio())
