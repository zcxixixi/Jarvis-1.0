import os
import json
import uuid
import asyncio
import websockets
import re
from dotenv import load_dotenv
from jarvis_assistant.services.doubao.protocol import DoubaoMessage, MsgType, EventType, SerializationBits

# Robustly load .env
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path, override=True)

class BidirectionalTTS:
    def __init__(self):
        from jarvis_assistant.config.doubao_config import TTS_2_0_CONFIG
        self.endpoint = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
        # [DEBUG] Force Hardcoded values to match working test_tts_module.py
        self.appid = "3284176421"
        self.access_token = "elO_bo1SMiqeKF5_J0uIFFT6VjNAPLV0"
        
        self.voice_type = "zh_male_lengkugege_emo_v2_mars_bigtts"  # [FIX] Working male voice
        self.resource_id = "volc.service_type.10029"  # 对齐 Demo 资源ID
        self.emotion_scale = TTS_2_0_CONFIG["emotion_scale"]
        
        self.ws = None
        self.session_id = None
        self.is_connected = False
        self._audio_queue = asyncio.Queue()
        self._receive_task = None
        self._active_session = False
        self._event_futures = {} 
        self._current_emotion = "coldness"

    async def connect(self):
        if self.is_connected: return
        
        # [STRICT] Follow demo header format exactly
        headers = {
            "X-Api-App-Key": self.appid,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }
        
        try:
            # print(f"DEBUG: Connecting to {self.endpoint} with Resource-Id: {self.resource_id}")
            # Ensure we use a fresh connect with proper headers
            self.ws = await websockets.connect(self.endpoint, additional_headers=headers, max_size=10*1024*1024)
            self.is_connected = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            # Connection phase
            await self._wait_for_event(EventType.ConnectionStarted)
            print(f"[TTS 2.0] ✅ Expressive Link Active")
        except Exception as e:
            self.is_connected = False
            print(f"[TTS 2.0] ❌ Connection failed: {e}")

    async def _wait_for_event(self, event_type, timeout=5.0):
        fut = asyncio.get_running_loop().create_future()
        self._event_futures[event_type] = fut
        try:
            if event_type == EventType.ConnectionStarted:
                msg = DoubaoMessage(type=MsgType.FullClientRequest, event=EventType.StartConnection, payload=b"{}")
                await self.ws.send(msg.marshal())
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._event_futures.pop(event_type, None)

    async def _receive_loop(self):
        try:
            async for message in self.ws:
                if not self.is_connected: break
                msg = DoubaoMessage.from_bytes(message)
                
                # Wake futures
                if msg.event in self._event_futures:
                    if not self._event_futures[msg.event].done():
                        self._event_futures[msg.event].set_result(msg)
                
                # Audio flow
                if msg.serialization == SerializationBits.Raw:
                    await self._audio_queue.put(msg.payload)
                elif msg.event == EventType.SessionFinished:
                    await self._audio_queue.put(None) 
                    self._active_session = False
                elif msg.type == MsgType.Error:
                    print(f"[TTS 2.0] ❌ Server Error: {msg.payload.decode('utf-8', 'ignore')}")
                    # Release any waiters on error
                    for f in self._event_futures.values():
                        if not f.done(): f.set_exception(RuntimeError("TTS Error"))
        except Exception as e:
            # print(f"[TTS 2.0] Receive Loop ended: {e}")
            pass

    async def start_session(self, emotion: str = None):
        if not self.is_connected: await self.connect()
        if not self.is_connected: return
        
        if emotion: self._current_emotion = emotion
        self.session_id = str(uuid.uuid4())
        
        # Follow Demo Payload structure
        req = {
            "user": {"uid": "jarvis"},
            "namespace": "BidirectionalTTS",
            "req_params": {
                "speaker": self.voice_type,
                "audio_params": {
                    "format": "pcm",
                    "sample_rate": 24000,
                    # [FIX] Simplified to match working demo (10029 doesn't support emotion params?)
                    # "emotion": self._current_emotion, 
                    # "emotion_scale": self.emotion_scale
                },
                # "additions": json.dumps({"use_tag_parser": True}),
            },
            "event": EventType.StartSession
        }
        
        fut = asyncio.get_running_loop().create_future()
        self._event_futures[EventType.SessionStarted] = fut
        msg = DoubaoMessage(type=MsgType.FullClientRequest, event=EventType.StartSession, session_id=self.session_id, payload=json.dumps(req).encode('utf-8'))
        await self.ws.send(msg.marshal())
        
        # [FIX] Wait for SessionStarted before marking active
        try:
            await asyncio.wait_for(fut, timeout=5.0)
            self._active_session = True
        except asyncio.TimeoutError:
            print("[TTS 2.0] ❌ Session Start Timeout")
            self._active_session = False
            raise
            
    async def send_text(self, text: str):
        if not self.is_connected: return
        emotion = None
        match = re.search(r'\[([a-zA-Z_\-]+)\]', text)
        if match:
            emotion = match.group(1)
            text = text.replace(f'[{emotion}]', '').strip()

        if not self._active_session or (emotion and emotion != self._current_emotion):
            if self._active_session: await self.finish_session()
            await self.start_session(emotion=emotion)
            
        req_params = {
            "text": text
        }
        if emotion:
             # Only add emotion if strictly needed and supported (removed for 10029 stability)
             pass

        req = {
            "namespace": "BidirectionalTTS",
            "req_params": req_params,
            "event": EventType.TaskRequest
        }
        msg = DoubaoMessage(type=MsgType.FullClientRequest, event=EventType.TaskRequest, session_id=self.session_id, payload=json.dumps(req).encode('utf-8'))
        await self.ws.send(msg.marshal())

    async def finish_session(self):
        if self._active_session:
            msg = DoubaoMessage(type=MsgType.FullClientRequest, event=EventType.FinishSession, session_id=self.session_id, payload=b"{}")
            try: await self.ws.send(msg.marshal())
            except: pass
            self._active_session = False

    async def audio_stream(self):
        while True:
            chunk = await self._audio_queue.get()
            if chunk is None: break
            yield chunk

    async def close(self):
        self.is_connected = False
        if self.ws:
            msg = DoubaoMessage(type=MsgType.FullClientRequest, event=EventType.FinishConnection, payload=b"{}")
            try: await self.ws.send(msg.marshal())
            except: pass
            await self.ws.close()
