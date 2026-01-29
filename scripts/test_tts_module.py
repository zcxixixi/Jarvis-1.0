
import asyncio
import json
import os
import uuid
import websockets
from dotenv import load_dotenv

# Load env
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root) # [FIX] Add project root to path
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path, override=True)

from jarvis_assistant.services.doubao.protocol import DoubaoMessage, MsgType, EventType, SerializationBits
from jarvis_assistant.config.doubao_config import TTS_2_0_CONFIG

TTS_ENDPOINT = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
TTS_ENDPOINT = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
# Credentials provided by user
APP_ID = "3284176421"
ACCESS_TOKEN = "elO_bo1SMiqeKF5_J0uIFFT6VjNAPLV0"

async def test_tts_module():
    # The confirmed working pair for this AppID
    res_id = "volc.service_type.10029"
    spk = "zh_female_cancan_mars_bigtts"
    
    print(f"\n🚀 Starting Jarvis TTS Demonstration...")
    print(f"🔧 Configuration: Resource={res_id}, Speaker={spk}")
    
    headers = {
        "X-Api-App-Key": APP_ID,
        "X-Api-Access-Key": ACCESS_TOKEN,
        "X-Api-Resource-Id": res_id,
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }
    
    try:
        async with websockets.connect(TTS_ENDPOINT, additional_headers=headers) as ws:
            # 1. Start Connection
            msg = DoubaoMessage(type=MsgType.FullClientRequest, event=EventType.StartConnection, payload=b"{}")
            await ws.send(msg.marshal())
            
            # Wait for ConnectionStarted
            while True:
                resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
                m = DoubaoMessage.from_bytes(resp)
                if m.event == EventType.ConnectionStarted:
                    print("   ✅ Connection Established")
                    break
                elif m.event == EventType.ConnectionFailed:
                    print(f"   ❌ Connection Failed: {m.payload.decode('utf-8')}")
                    return

            # 2. Start Session
            session_id = str(uuid.uuid4())
            req = {
                "user": {"uid": "jarvis_demo"},
                "namespace": "BidirectionalTTS",
                "req_params": {
                    "speaker": spk,
                    "audio_params": {"format": "pcm", "sample_rate": 24000},
                },
                "event": EventType.StartSession
            }
            msg = DoubaoMessage(type=MsgType.FullClientRequest, event=EventType.StartSession, session_id=session_id, payload=json.dumps(req).encode('utf-8'))
            await ws.send(msg.marshal())

            # Wait for SessionStarted
            while True:
                resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
                m = DoubaoMessage.from_bytes(resp)
                if m.event == EventType.SessionStarted:
                    print("   ✅ Session Started")
                    break
                elif m.type == MsgType.Error or m.event == EventType.SessionFailed:
                    print(f"   ❌ Session Failed: {m.payload.decode('utf-8')}")
                    return
            
            # 3. Send Task Request (Actual Text)
            text = "先生，今天苹果股价二百五十六，特斯拉四百三十一。"
            print(f"   🎙️ Synthesizing: \"{text}\"")
            text_req = {
                "namespace": "BidirectionalTTS",
                "req_params": {"text": text},
                "event": EventType.TaskRequest
            }
            msg = DoubaoMessage(type=MsgType.FullClientRequest, event=EventType.TaskRequest, session_id=session_id, payload=json.dumps(text_req).encode('utf-8'))
            await ws.send(msg.marshal())
            
            # 4. Receive Audio
            audio_count = 0
            with open("tts_demo_output.pcm", "wb") as f:
                while True:
                    try:
                        resp = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        m = DoubaoMessage.from_bytes(resp)
                        if m.serialization == SerializationBits.Raw:
                            f.write(m.payload)
                            audio_count += 1
                            if audio_count == 1: print("   🔊 Receiving Audio", end="")
                            if audio_count % 10 == 0: print(".", end="", flush=True)
                        elif m.event == EventType.SessionFinished:
                            print(f"\n   ✅ Synthesis Complete! {audio_count} chunks received.")
                            break
                        elif m.type == MsgType.Error:
                            print(f"\n   ❌ Server Error: {m.payload.decode('utf-8')}")
                            break
                    except asyncio.TimeoutError:
                        print("\n   ⚠️ Timeout waiting for audio")
                        break
            
            print(f"   🎉 Success! Audio saved to tts_demo_output.pcm")
                
    except Exception as e:
        print(f"❌ Demo Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts_module())
