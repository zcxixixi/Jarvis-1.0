#!/usr/bin/env python3
"""
Test Doubao TTS output (text -> audio frames)
Usage: python3 test_doubao_tts_text.py "你好，先生"
"""
import asyncio
import gzip
import json
import os
import sys
import uuid
import wave
import ssl
import websockets
from dotenv import load_dotenv

# Project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(PROJECT_ROOT)

# Load env
load_dotenv(os.path.join(PROJECT_ROOT, "jarvis_assistant", ".env"), override=True)

from jarvis_assistant.config.doubao_config import ws_connect_config, start_session_req
from jarvis_assistant.services.doubao.protocol import DoubaoProtocol

async def main():
    text = sys.argv[1] if len(sys.argv) > 1 else "你好，先生。我是Jarvis。"
    mode = "tts"
    if len(sys.argv) > 2 and sys.argv[2] == "--chat":
        mode = "chat"
    session_id = str(uuid.uuid4())

    headers = ws_connect_config["headers"].copy()
    headers["X-Api-Connect-Id"] = str(uuid.uuid4())

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    ws = await websockets.connect(ws_connect_config["base_url"], additional_headers=headers, ssl=ssl_ctx, ping_interval=None)
    print("✅ Connected")

    # StartConnection
    req = bytearray(DoubaoProtocol.generate_header())
    req.extend((1).to_bytes(4, "big"))
    payload = gzip.compress(b"{}")
    req.extend(len(payload).to_bytes(4, "big"))
    req.extend(payload)
    await ws.send(req)
    await ws.recv()

    # StartSession
    config_payload = json.loads(json.dumps(start_session_req))
    config_payload["dialog"]["extra"]["input_mod"] = "text"
    config_payload["tts"]["audio_config"]["format"] = "pcm_s16le"

    req = bytearray(DoubaoProtocol.generate_header())
    req.extend((100).to_bytes(4, "big"))
    session_bytes = session_id.encode("utf-8")
    req.extend(len(session_bytes).to_bytes(4, "big"))
    req.extend(session_bytes)
    payload = gzip.compress(json.dumps(config_payload).encode("utf-8"))
    req.extend(len(payload).to_bytes(4, "big"))
    req.extend(payload)
    await ws.send(req)
    await ws.recv()

    # Send request (TTS or Chat)
    if mode == "chat":
        payload_obj = {"content": text}
        event_id = 501
        label = "CHAT"
    else:
        payload_obj = {"start": True, "end": True, "content": text}
        event_id = 500
        label = "TTS"

    payload = gzip.compress(json.dumps(payload_obj).encode("utf-8"))
    req = bytearray(DoubaoProtocol.generate_header())
    req.extend((event_id).to_bytes(4, "big"))
    req.extend(len(session_bytes).to_bytes(4, "big"))
    req.extend(session_bytes)
    req.extend(len(payload).to_bytes(4, "big"))
    req.extend(payload)
    await ws.send(req)
    print(f"📤 {label} request sent: {text}")

    audio_chunks = []
    got_text = False
    done = False
    start_time = asyncio.get_event_loop().time()

    try:
        while True:
            # hard timeout
            if asyncio.get_event_loop().time() - start_time > 15:
                print("⚠️ TTS wait timeout.")
                break
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                if audio_chunks or got_text:
                    break
                continue

            if len(message) < 8:
                continue

            header_size = message[0] & 0x0F
            payload_start = header_size * 4
            flags = message[1] & 0x0F
            if flags & 0x4:
                payload_start += 4

            session_len = int.from_bytes(message[payload_start:payload_start+4], 'big')
            payload_start += 4 + session_len

            payload_len = int.from_bytes(message[payload_start:payload_start+4], 'big')
            payload = message[payload_start+4:payload_start+4+payload_len]

            compress_type = message[2] & 0x0F
            if compress_type == 0x1:
                try:
                    payload = gzip.decompress(payload)
                except:
                    pass

            serial_type = message[2] >> 4
            if serial_type == 0x0:
                audio_chunks.append(payload)
                continue
            elif serial_type == 0x1:
                try:
                    event = json.loads(payload)
                    if "content" in event:
                        got_text = True
                        print(f"[CONTENT]: {event.get('content')}")
                    if event.get("type") == "Error":
                        print(f"❌ API Error: {event}")
                        break
                    if event.get("no_content") is True:
                        done = True
                        break
                except Exception:
                    pass

        if audio_chunks:
            out_path = "/tmp/jarvis_tts_output.wav"
            with wave.open(out_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(b"".join(audio_chunks))
            print(f"✅ TTS audio saved: {out_path} ({len(audio_chunks)} chunks)")
        else:
            print("⚠️ No TTS audio frames received.")
    finally:
        await ws.close()

if __name__ == "__main__":
    asyncio.run(main())
