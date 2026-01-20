import asyncio
import wave
import os
import sys
import gzip
import json
import uuid
import websockets
import ssl
import time
import pyaudio
from dotenv import load_dotenv

# Define project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

# Load env
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

# Import config
from jarvis_doubao_config import APP_ID, ACCESS_TOKEN, ws_connect_config
WS_URL = ws_connect_config["base_url"]
from jarvis_doubao_realtime import DoubaoProtocol

class DoubaoLatencyTester:
    def __init__(self, file_path):
        self.file_path = file_path
        self.session_id = str(uuid.uuid4())
        self.ws = None
        self.is_streaming = True
        self.audio_sent_time = 0
        self.first_audio_received = False
        self.p = pyaudio.PyAudio()

    async def connect(self):
        headers = {
            "X-Api-App-ID": APP_ID,
            "X-Api-Access-Key": ACCESS_TOKEN,
            "X-Api-Resource-Id": "volc.speech.dialog",
            "X-Api-App-Key": "PlgvMymc7f3tQnJ6",
            "X-Api-Connect-Id": str(uuid.uuid4())
        }
        
        print(f"🤖 Connecting to Doubao (Latency Test Mode)...")
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            async with websockets.connect(WS_URL, additional_headers=headers, ssl=ssl_ctx, ping_interval=None) as ws:
                self.ws = ws
                print("✅ Connected!")
                
                await self.send_start_connection()
                await self.send_start_session()
                
                print(f"🎙️ Streaming & Playing: {self.file_path}")
                # Use a larger gather to wait for receive_loop specifically
                await asyncio.gather(self.receive_loop(), self.stream_and_play())
                
        except Exception as e:
            print(f"❌ Error in connect: {e}")
        finally:
            self.p.terminate()

    async def send_start_connection(self):
        req = bytearray(DoubaoProtocol.generate_header())
        req.extend((1).to_bytes(4, 'big'))
        payload = gzip.compress(b"{}")
        req.extend(len(payload).to_bytes(4, 'big'))
        req.extend(payload)
        await self.ws.send(req)
        await self.ws.recv() 
        print("   StartConnection OK")

    async def send_start_session(self):
        config_payload = {
            "asr": {"extra": {"end_smooth_window_ms": 1500}},
            "tts": {
                "speaker": "zh_male_yunzhou_jupiter_bigtts",
                "audio_config": {"channel": 1, "format": "pcm_s16le", "sample_rate": 24000}
            },
            "dialog": {
                "bot_name": "Jarvis",
                "system_role": "你是Jarvis，一个由你的主人（即当前正在和你说话的人）亲自开发的顶级AI管家。说话保持冷静、专业、带有高级智能的从容。用中文回复。",
                "extra": {"strict_audit": False, "input_mod": "audio"}
            }
        }
        req = bytearray(DoubaoProtocol.generate_header())
        req.extend((100).to_bytes(4, 'big'))
        session_bytes = self.session_id.encode('utf-8')
        req.extend(len(session_bytes).to_bytes(4, 'big'))
        req.extend(session_bytes)
        payload = gzip.compress(json.dumps(config_payload).encode('utf-8'))
        req.extend(len(payload).to_bytes(4, 'big'))
        req.extend(payload)
        await self.ws.send(req)
        await self.ws.recv()
        print("   StartSession OK")

    async def stream_and_play(self):
        with wave.open(self.file_path, 'rb') as wf:
            rate = wf.getframerate()
            channels = wf.getnchannels()
            stream = self.p.open(format=self.p.get_format_from_width(wf.getsampwidth()),
                                channels=channels,
                                rate=rate,
                                output=True)
            
            chunk_duration = 0.1 # 100ms
            chunk_size = int(rate * chunk_duration)
            
            data = wf.readframes(chunk_size)
            while data:
                # 1. Send to API
                req = bytearray(DoubaoProtocol.generate_header(message_type=0x2, serial=0x0, compress=0x1))
                req.extend((200).to_bytes(4, 'big'))
                session_bytes = self.session_id.encode('utf-8')
                req.extend(len(session_bytes).to_bytes(4, 'big'))
                req.extend(session_bytes)
                payload = gzip.compress(data)
                req.extend(len(payload).to_bytes(4, 'big'))
                req.extend(payload)
                await self.ws.send(req)
                
                # 2. Play locally
                stream.write(data)
                
                await asyncio.sleep(0.01) # Small sleep to ensure loop yields
                data = wf.readframes(chunk_size)
            
            stream.stop_stream()
            stream.close()
            
        print("✅ Input audio finished streaming.")
        self.audio_sent_time = time.time()
        self.is_streaming = False

    async def receive_loop(self):
        output_stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)
        print("   [DEBUG] Receive loop started")
        
        try:
            while True:
                try:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    if not self.is_streaming:
                        print("\n   [DEBUG] Stream ended, checking for final responses...")
                        # Wait a bit more for final processing
                        await asyncio.sleep(3.0)
                        break
                    continue

                if len(message) < 8: continue
                
                header_size = message[0] & 0x0F
                payload_start = header_size * 4
                flags = message[1] & 0x0F
                if flags & 0x4: payload_start += 4
                
                session_len = int.from_bytes(message[payload_start:payload_start+4], 'big')
                payload_start += 4 + session_len
                
                payload_len = int.from_bytes(message[payload_start:payload_start+4], 'big')
                payload = message[payload_start+4:payload_start+4+payload_len]
                
                compress_type = message[2] & 0x0F
                if compress_type == 0x1:
                    try: payload = gzip.decompress(payload)
                    except: pass
                
                serial_type = message[2] >> 4
                if serial_type == 0x0: # Audio
                    if not self.first_audio_received and not self.is_streaming:
                        latency = (time.time() - self.audio_sent_time) * 1000
                        print(f"\n⏱️  [Latency]: Jarvis responded in {latency:.2f}ms")
                        self.first_audio_received = True
                    output_stream.write(payload)
                    print(".", end="", flush=True)
                elif serial_type == 0x1: # JSON
                    try:
                        event = json.loads(payload)
                        print(f"\n[DEBUG EVENT]: {json.dumps(event, ensure_ascii=False)}")
                        if "asr" in event:
                            print(f"\n[ASR]: {event['asr'].get('text', '')}")
                        if "tts" in event:
                            print(f"\n[TTS]: {event['tts'].get('text', '')}")
                        if "content" in event:
                            print(f"\n[CONTENT]: {event['content']}")
                        if event.get("type") == "Error":
                            print(f"\n❌ API Error: {event}")
                    except: pass
        finally:
            output_stream.stop_stream()
            output_stream.close()
            print("\n   [DEBUG] Receive loop finished")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_doubao_audio_file.py <wav_file>")
        sys.exit(1)
    tester = DoubaoLatencyTester(sys.argv[1])
    asyncio.run(tester.connect())
