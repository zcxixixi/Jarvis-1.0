
import asyncio
import websockets
import json
import pyaudio
import uuid
import struct
import gzip

# ================= CONFIGURATION =================
APP_ID = "3805698959"
ACCESS_TOKEN = "O_kHQrT-iRJaVDfB6CJDRqJLrWiIKwcDaP"
WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue" 

class DoubaoProtocol:
    @staticmethod
    def generate_header(message_type=0x1, flags=0x4, serial=0x1, compress=0x1):
        # Header: Version(4) + Size(4) | Type(4) + Flags(4) | Serial(4) + Compress(4) | Reserved(8)
        return bytearray([
            0x11,  # Version 1, Size 1 (4 bytes)
            (message_type << 4) | flags,
            (serial << 4) | compress,
            0x00
        ])

class DoubaoRealtimeJarvis:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.ws = None
        self.session_id = str(uuid.uuid4())
        self.is_running = True

    async def connect(self):
        import ssl
        
        headers = {
            "X-Api-App-ID": APP_ID,
            "X-Api-Access-Key": ACCESS_TOKEN,
            "X-Api-Resource-Id": "volc.speech.dialog",
            "X-Api-App-Key": "PlgvMymc7f3tQnJ6",
            "X-Api-Connect-Id": str(uuid.uuid4())
        }
        
        print(f"🤖 Connecting to Doubao...")
        
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            async with websockets.connect(WS_URL, additional_headers=headers, ssl=ssl_ctx, ping_interval=None) as ws:
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
            req = bytearray(DoubaoProtocol.generate_header(message_type=0x2, serial=0x0, compress=0x1))
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
                    if event.get('type') == 'Error':
                        print(f"\n❌ {event}")
                except: pass
            elif serial_type == 0x0:  # Audio!
                self.output_stream.write(payload)
                print(".", end="", flush=True)

if __name__ == "__main__":
    j = DoubaoRealtimeJarvis()
    asyncio.run(j.connect())
