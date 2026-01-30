import os
import json
import uuid
import asyncio
import gzip
import websockets
import logging
from dotenv import load_dotenv
from jarvis_assistant.services.doubao.protocol import (
    MsgType, MsgTypeFlagBits, SerializationBits, CompressionBits
)

# Load env
load_dotenv(override=True)

from jarvis_assistant.config.doubao_config import APP_ID, ACCESS_TOKEN

TTS_WS_URL = os.getenv("DOUBAO_TTS_WS_URL", "wss://openspeech.bytedance.com/api/v1/tts/ws_binary")
# APP_ID and ACCESS_TOKEN imported from doubao_config
APP_TOKEN = ACCESS_TOKEN # [FIX] Use the actual token instead of literal "token"
CLUSTER = os.getenv("DOUBAO_TTS_CLUSTER", "volcano_tts")
# [FIX] Use exact numeric Resource ID provided by user
RESOURCE_ID = "2000000593268532578" 
# [FIX] Selected Male voice (SeedTTS 2.0)
VOICE_TYPE = "zh_male_m191_uranus_bigtts" 
ENCODING = "pcm"
SAMPLE_RATE = 24000
SPEED = 1.0
VOLUME = 1.0

logger = logging.getLogger(__name__)

# Protocol constants
PROTOCOL_VERSION = 0b0001

def generate_header(message_type=MsgType.FullClientRequest, flags=MsgTypeFlagBits.NoSeq):
    """Generate binary protocol header."""
    header = bytearray()
    header.append((PROTOCOL_VERSION << 4) | 1)  # version | header_size
    header.append((int(message_type) << 4) | int(flags))
    header.append((int(SerializationBits.JSON) << 4) | int(CompressionBits.Gzip))
    header.append(0x00)  # reserved
    return header

def parse_response(res):
    """Parse binary response from TTS server."""
    message_type = res[1] >> 4
    header_size = res[0] & 0x0f
    compression = res[2] & 0x0f
    payload = res[header_size * 4:]
    result = {'message_type': message_type}
    
    # Audio response (AudioOnlyServer = 0b1011 = 11)
    if message_type == 11:
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['seq'] = seq
        if len(payload) >= 8:
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            audio_data = payload[8:8+payload_size]
            result['audio'] = audio_data
    # Full response
    elif message_type == 9:
        payload_size = int.from_bytes(payload[:4], "big", signed=True)
        payload_msg = payload[4:4+payload_size]
        if compression == 1:  # GZIP
            payload_msg = gzip.decompress(payload_msg)
        result['payload_msg'] = json.loads(payload_msg.decode('utf-8'))
    # Error response
    elif message_type == 15:
        code = int.from_bytes(payload[:4], "big", signed=False)
        result['code'] = code
        if len(payload) >= 8:
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:8+payload_size]
            if compression == 1:
                payload_msg = gzip.decompress(payload_msg)
            result['payload_msg'] = json.loads(payload_msg.decode('utf-8'))
    
    return result

class DoubaoTTSV1:
    """Manages a persistent WebSocket connection to Doubao TTS V1 Binary API."""
    
    def __init__(self):
        self.ws = None
        self.lock = asyncio.Lock() # Prevents overlapping requests on same WS
        self.headers = {
            "X-Api-App-Key": APP_ID,
            "X-Api-Access-Key": ACCESS_TOKEN,
            "X-Api-Resource-Id": RESOURCE_ID,
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

    def _is_closed(self):
        """Super-robust check to avoid AttributeError on different websockets versions."""
        if self.ws is None:
            return True
        try:
            # 1. Standard approach
            if hasattr(self.ws, 'closed'):
                return self.ws.closed
            # 2. Alternative approach
            if hasattr(self.ws, 'open'):
                return not self.ws.open
            # 3. Connection state approach (websockets 13+)
            if hasattr(self.ws, 'protocol') and hasattr(self.ws.protocol, 'state'):
                from websockets.protocol import State
                return self.ws.protocol.state is State.CLOSED
            # 4. Final fallback
            return False # Assume open if we can't tell, the next call will fail and we'll reset
        except Exception:
            return True # If in doubt, assume closed to trigger reconnect

    async def connect(self):
        if not self._is_closed():
            return
        print(f"🔥 [TTS V1] Establishing persistent connection to: {TTS_WS_URL}")
        try:
            self.ws = await websockets.connect(TTS_WS_URL, additional_headers=self.headers)
        except Exception as e:
            print(f"❌ [TTS V1] Connection failed: {e}")
            self.ws = None

    async def synthesize(self, text: str):
        """Synthesize text and yield PCM chunks over the open WebSocket. Thread-safe."""
        async with self.lock:
            if self._is_closed():
                await self.connect()
            
            if not self.ws:
                print("❌ [TTS V1] Cannot synthesize: No connection.")
                return

            request_json = {
                "app": {"appid": APP_ID, "token": APP_TOKEN, "cluster": CLUSTER},
                "user": {"uid": "jarvis_user"},
                "audio": {
                    "voice_type": VOICE_TYPE,
                    "encoding": ENCODING,
                    "rate": SAMPLE_RATE,
                    "speed_ratio": SPEED,
                    "volume_ratio": VOLUME,
                },
                "request": {
                    "reqid": str(uuid.uuid4()),
                    "text": text,
                    "operation": "submit",
                    "with_timestamp": 1,
                }
            }

            try:
                payload_bytes = gzip.compress(json.dumps(request_json).encode("utf-8"))
                packet = bytearray(generate_header())
                packet.extend(len(payload_bytes).to_bytes(4, "big"))
                packet.extend(payload_bytes)
                await self.ws.send(packet)

                while True:
                    response = await self.ws.recv()
                    parsed = parse_response(response)
                    
                    if 'audio' in parsed:
                        yield parsed['audio']
                        if parsed.get('seq', 0) < 0:
                            break
                    elif parsed.get('code', 0) not in [0, 1000, 3000]:
                        logger.error(f"TTS Error: {parsed}")
                        break
            except Exception as e:
                print(f"❌ [TTS V1] Stream error: {e}")
                self.ws = None # Mark for reconnect
                raise

    async def close(self):
        if not self._is_closed():
            await self.ws.close()
            self.ws = None

# Legacy function (now uses internal instance for simplicity but creates a new one each time)
# Better to use the class directly for persistence.
async def synthesize_stream(text: str):
    """Generate audio stream from text. (Legacy: Creates new connection per call)"""
    tts = DoubaoTTSV1()
    try:
        await tts.connect()
        async for chunk in tts.synthesize(text):
            yield chunk
    finally:
        await tts.close()

async def speak_text(text: str):
    # ... legacy code ...
    pass
