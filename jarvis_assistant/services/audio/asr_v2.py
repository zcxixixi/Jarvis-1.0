import asyncio
import base64
import gzip
import json
import logging
import uuid
import websockets
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Protocol Constants from official demo
PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001
CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111
NO_SEQUENCE = 0b0000
NEG_SEQUENCE = 0b0010
JSON = 0b0001
GZIP = 0b0001

def generate_header(
    version=PROTOCOL_VERSION,
    message_type=CLIENT_FULL_REQUEST,
    message_type_specific_flags=NO_SEQUENCE,
    serial_method=JSON,
    compression_type=GZIP,
    reserved_data=0x00,
    extension_header=bytes()
):
    header = bytearray()
    header_size = int(len(extension_header) / 4) + 1
    header.append((version << 4) | header_size)
    header.append((message_type << 4) | message_type_specific_flags)
    header.append((serial_method << 4) | compression_type)
    header.append(reserved_data)
    header.extend(extension_header)
    return header

def parse_response(res):
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0f
    reserved = res[3]
    payload = res[header_size * 4:]
    
    result = {"message_type": message_type}
    payload_msg = None
    
    if message_type == SERVER_FULL_RESPONSE:
        payload_msg = payload[4:]
    elif message_type == SERVER_ACK:
        result['seq'] = int.from_bytes(payload[:4], "big", signed=True)
        if len(payload) >= 8:
            payload_msg = payload[8:]
    elif message_type == SERVER_ERROR_RESPONSE:
        result['code'] = int.from_bytes(payload[:4], "big", signed=False)
        payload_msg = payload[8:]
        
    if payload_msg is None: return result
    if message_compression == GZIP:
        try: payload_msg = gzip.decompress(payload_msg)
        except: pass
        
    if serialization_method == JSON:
        try: payload_msg = json.loads(str(payload_msg, "utf-8"))
        except: pass
    
    result['payload'] = payload_msg
    return result

class ASRServiceV2:
    def __init__(self, appid: str, token: str, cluster: str):
        self.appid = appid
        self.token = token
        self.cluster = cluster
        self.ws_url = "wss://openspeech.bytedance.com/api/v2/asr"
        self.ws = None
        self._running = False
        self.on_transcription = None # Callback(text, is_final)

    def _construct_init_request(self):
        return {
            'app': {'appid': self.appid, 'cluster': self.cluster, 'token': self.token},
            'user': {'uid': 'jarvis_asr_v2'},
            'request': {
                'reqid': str(uuid.uuid4()),
                'workflow': 'audio_in,resample,partition,vad,fe,decode,itn,nlu_punctuate',
                'result_type': 'full',
                'sequence': 1
            },
            'audio': {
                'format': 'pcm',
                'rate': 16000,
                'language': 'zh-CN',
                'bits': 16,
                'channel': 1,
                'codec': 'raw'
            }
        }

    async def connect(self):
        # [FIX] For websockets >= 14.0/16.0, use 'additional_headers' or just direct kwargs?
        # Actually in 10.0+ it became 'additional_headers' for the high level API but 'extra_headers' strictly for handshake? 
        # Check source: websockets 16.0 client.connect implementation.
        # It accepts **kwargs and passes them to the handshake.
        # It seems 'additional_headers' is preferred in some contexts.
        # Let's try 'additional_headers'.
        
        header = {'Authorization': f'Bearer; {self.token}'}
        # If 'additional_headers' fails, we will try to pass headers directly or update code.
        self.ws = await websockets.connect(self.ws_url, additional_headers=header)
        
        # Send Full Client Request (Init)
        req = self._construct_init_request()
        payload = gzip.compress(json.dumps(req).encode('utf-8'))
        full_req = bytearray(generate_header())
        full_req.extend(len(payload).to_bytes(4, 'big'))
        full_req.extend(payload)
        await self.ws.send(full_req)
        
        # Wait for first ACK
        resp = await self.ws.recv()
        result = parse_response(resp)
        if result.get('payload', {}).get('code') != 1000:
            raise Exception(f"ASR Init Failed: {result}")
        
        self._running = True
        asyncio.create_task(self._receive_loop())
        logger.info("ASR v2 Connected.")

    async def _receive_loop(self):
        try:
            while self._running:
                resp = await self.ws.recv()
                result = parse_response(resp)
                payload = result.get('payload', {})
                
                if 'text' in payload:
                    text = payload['text']
                    is_final = payload.get('is_final', False)
                    if self.on_transcription:
                        await self.on_transcription(text, is_final)
                
                if payload.get('code') and payload.get('code') != 1000:
                    logger.error(f"ASR Error: {payload}")
        except Exception as e:
            if self._running: logger.error(f"ASR Recv Loop Error: {e}")

    async def send_audio(self, chunk: bytes, is_last: bool = False):
        if not self.ws or not self._running: return
        
        payload = gzip.compress(chunk)
        flags = NEG_SEQUENCE if is_last else NO_SEQUENCE
        header = generate_header(message_type=CLIENT_AUDIO_ONLY_REQUEST, message_type_specific_flags=flags)
        
        msg = bytearray(header)
        msg.extend(len(payload).to_bytes(4, 'big'))
        msg.extend(payload)
        await self.ws.send(msg)

    async def close(self):
        self._running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
