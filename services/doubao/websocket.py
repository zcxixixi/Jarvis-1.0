
import asyncio
import websockets
import json
import pyaudio
import uuid
import struct
import gzip

# ================= CONFIGURATION =================
# ================= CONFIGURATION =================
from jarvis_assistant.config.doubao_config import APP_ID, ACCESS_TOKEN, ws_connect_config 
from jarvis_assistant.services.doubao.protocol import DoubaoProtocol


class DoubaoRealtimeJarvis:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.ws = None
        self.session_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        self.is_running = True
        
    async def on_text_received(self, text: str):
        """Override this to handle user text"""
        print(f"📝 User said: {text}")

    async def connect(self):
        import ssl
        
        # Merge setup from config
        headers = ws_connect_config["headers"].copy()
        headers["X-Api-Connect-Id"] = str(uuid.uuid4())
        ws_url = ws_connect_config["base_url"]
        
        print(f"🤖 Connecting to Doubao...")
        
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            async with websockets.connect(ws_url, additional_headers=headers, ssl=ssl_ctx, ping_interval=None) as ws:
                self.ws = ws
                print("✅ Connected!")
                
                # 1. StartConnection (Event 1)
                await self.send_start_connection()
                
                # 2. StartSession (Event 100)
                await self.send_start_session()
                
                # 3. Audio
                self.setup_audio()
                print("🎙️ Jarvis is alive. Speak!")
                
                await asyncio.gather(self.receive_loop(), self.send_audio_loop())
                
        except Exception as e:
            print(f"❌ Error: {e}")

    async def send_start_connection(self):
        # Header
        req = bytearray(DoubaoProtocol.generate_header())
        # Event ID (1)
        req.extend((1).to_bytes(4, 'big'))
        # Payload
        payload = gzip.compress(b"{}")
        req.extend(len(payload).to_bytes(4, 'big'))
        req.extend(payload)
        
        await self.ws.send(req)
        resp = await self.ws.recv()
        print(f"   StartConnection OK")

    async def send_start_session(self):
        config_payload = {
            "asr": {
                "extra": {"end_smooth_window_ms": 1500}
            },
            "tts": {
                "speaker": "zh_male_yunzhou_jupiter_bigtts",
                "audio_config": {"channel": 1, "format": "pcm", "sample_rate": 24000}
            },
            "dialog": {
                "bot_name": "Jarvis",
                "system_role": "你是Jarvis，一个专业的AI助手。",
                "speaking_style": "简洁、清晰。",
                "extra": {
                    "strict_audit": False,
                    "recv_timeout": 10,
                    "input_mod": "audio"
                }
            }
        }
        
        # Header
        req = bytearray(DoubaoProtocol.generate_header())
        # Event ID (100)
        req.extend((100).to_bytes(4, 'big'))
        # Session ID
        session_bytes = self.session_id.encode('utf-8')
        req.extend(len(session_bytes).to_bytes(4, 'big'))
        req.extend(session_bytes)
        # Payload
        payload = gzip.compress(json.dumps(config_payload).encode('utf-8'))
        req.extend(len(payload).to_bytes(4, 'big'))
        req.extend(payload)
        
        await self.ws.send(req)
        resp = await self.ws.recv()
        print(f"   StartSession OK")

    def setup_audio(self):
        self.input_stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=3200)
        self.output_stream = self.p.open(format=pyaudio.paFloat32, channels=1, rate=24000, output=True)

    async def send_audio_loop(self):
        while self.is_running:
            # Read 3200 bytes (200ms @ 16kHz)
            audio = self.input_stream.read(3200, exception_on_overflow=False)
            
            # Header (Audio Only, No JSON)
            req = bytearray(DoubaoProtocol.generate_header(
                message_type=DoubaoProtocol.CLIENT_AUDIO_ONLY_REQUEST,
                serial_method=DoubaoProtocol.NO_SERIALIZATION
            ))
            # Event ID (200)
            req.extend((200).to_bytes(4, 'big'))
            # Session ID
            session_bytes = self.session_id.encode('utf-8')
            req.extend(len(session_bytes).to_bytes(4, 'big'))
            req.extend(session_bytes)
            # Audio payload (Gzipped)
            payload = gzip.compress(audio)
            req.extend(len(payload).to_bytes(4, 'big'))
            req.extend(payload)
            
            await self.ws.send(req)
            await asyncio.sleep(0.01)

    async def receive_loop(self):
        async for message in self.ws:
            # Parse header
            if len(message) < 8: continue
            msg_type = message[1] >> 4
            
            # Skip header
            header_size = message[0] & 0x0F
            payload_start = header_size * 4
            
            # Parse Event ID (if exists)
            flags = message[1] & 0x0F
            if flags & 0x4:
                event_id = int.from_bytes(message[payload_start:payload_start+4], 'big')
                payload_start += 4
            
            # Session ID
            session_len = int.from_bytes(message[payload_start:payload_start+4], 'big')
            payload_start += 4 + session_len
            
            # Payload
            payload_len = int.from_bytes(message[payload_start:payload_start+4], 'big')
            payload = message[payload_start+4:payload_start+4+payload_len]
            
            # Decompress
            compress_type = message[2] & 0x0F
            if compress_type == 0x1:
                try: payload = gzip.decompress(payload)
                except: pass
            
            # Audio or JSON?
            serial_type = message[2] >> 4
            if serial_type == 0x1:  # JSON
                try:
                    event = json.loads(payload)
                    # DEBUG: Print all events to find the ASR text
                    if 'content' in str(event): 
                        print(f"🔍 MSG: {event}")
                    
                    # Handle ASR Final Result
                    # Typical Volcengine event structure:
                    # {"type": "AudioInput", "state": "finished", "asr_text": "hello"}
                    # OR
                    # {"type": "ASR", "payload": {"text": "hello", "is_final": true}}
                    
                    event_type = event.get('type', '')
                    
                    if event_type == 'AudioInput' and event.get('state') == 'finished':
                        # Case 1: AudioInput finished
                        asr_text = event.get('asr_text') or event.get('text')
                        if asr_text:
                            # print(f"📝 ASR FINAL: {asr_text}")
                            asyncio.create_task(self.on_text_received(asr_text))
                            
                    elif 'asr_result' in event:
                        # Case 2: Explicit asr_result field
                        asr = event['asr_result']
                        if asr.get('is_final') or asr.get('status') == 'finished':
                             asyncio.create_task(self.on_text_received(asr.get('text', '')))
                             
                    # Fallback: check content field for simple text events
                    elif 'content' in event and 'user' in str(event.get('role', '')).lower():
                         asyncio.create_task(self.on_text_received(event['content']))

                    if event.get('type') == 'Error':
                        print(f"\n❌ {event}")
                        
                except: pass
            elif serial_type == 0x0:  # Audio!
                self.output_stream.write(payload)
                print(".", end="", flush=True)

if __name__ == "__main__":
    j = DoubaoRealtimeJarvis()
    asyncio.run(j.connect())
