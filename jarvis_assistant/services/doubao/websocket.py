
import asyncio
import websockets
import json
import pyaudio
import uuid
import struct
import gzip
import time

# ================= CONFIGURATION =================
from jarvis_assistant.config.doubao_config import APP_ID, ACCESS_TOKEN, ws_connect_config, start_session_req
from jarvis_assistant.services.doubao.protocol import DoubaoMessage, MsgType, EventType, SerializationBits


class DoubaoRealtimeJarvis:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.ws = None
        self.session_id = str(uuid.uuid4())
        self.is_running = True
        
    async def on_text_received(self, text: str):
        """Override this to handle user text"""
        print(f"📝 User said: {text}")

    async def connect(self):
        import ssl
        headers = ws_connect_config["headers"].copy()
        headers["X-Api-Connect-Id"] = str(uuid.uuid4())
        ws_url = ws_connect_config["base_url"]
        
        print(f"🤖 Connecting to Realtime API...")
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            async with websockets.connect(ws_url, additional_headers=headers, ssl=ssl_ctx, ping_interval=None) as ws:
                self.ws = ws
                print("✅ Realtime Connected!")
                
                await self.send_start_connection()
                await self.send_start_session()
                self.setup_audio()
                
                await asyncio.gather(self.receive_loop(), self.send_audio_loop())
                
        except Exception as e:
            print(f"❌ Connection Error: {e}")

    async def send_start_connection(self):
        msg = DoubaoMessage(type=MsgType.FullClientRequest, event=EventType.StartConnection, payload=b"{}")
        await self.ws.send(msg.marshal())
        # Wait for ConnectionStarted
        resp = await self.ws.recv()

    async def send_start_session(self):
        payload = json.dumps(start_session_req).encode('utf-8')
        msg = DoubaoMessage(type=MsgType.FullClientRequest, event=EventType.StartSession, session_id=self.session_id, payload=payload)
        
        print(f"[SESSION] 🚀 Starting {self.session_id[:8]}...")
        await self.ws.send(msg.marshal())
        resp = await self.ws.recv()
        
        try:
            m = DoubaoMessage.from_bytes(resp)
            if m.type == MsgType.Error:
                print(f"[SESSION] ❌ Start Failed: {m.payload.decode('utf-8')}")
            else:
                print(f"[SESSION] ✅ Started successfully.")
                # [FIX] Capture dialog_id for subsequent turns
                try:
                    payload = json.loads(m.payload)
                    self.dialog_id = payload.get('dialog_id')
                    print(f"[SESSION] 🆔 Dialog ID captured: {self.dialog_id}")
                except:
                    self.dialog_id = None
        except Exception as e:
             print(f"[SESSION] ⚠️ Response parse error: {e}")

    def setup_audio(self):
        pass

    async def send_audio_loop(self):
        pass

    async def send_text_query(self, text: str):
        if not self.ws: return
        
        # Ensure previous turn is finished
        if self.pending_response:
             await self._wait_for_turn_slot()

        # [FIX] 彻底回归最稳健的 TextInput 发送方式
        # 参考官方 Demo：使用 full_client_request 构建
        # 实时对话接口的 Event 101 是 TextInput
        payload = {
            "type": "TextInput",
            "content": text
        }
        
        # 使用官方协议对象的 marshal 逻辑，但手动指定 event 和 session_id
        msg = DoubaoMessage(
            type=MsgType.FullClientRequest, 
            event=101, 
            session_id=self.session_id, 
            payload=json.dumps(payload).encode('utf-8')
        )
        
        # [DEBUG]
        # print(f"DEBUG: Marshalling message with session_id: {self.session_id}")
        
        full_msg = msg.marshal()
        
        print(f"[REALTIME] 📤 TextInput: {text} | Session: {self.session_id[:8]} | MsgLen: {len(full_msg)}")
        try:
            await self.ws.send(full_msg)
        except Exception as e:
            print(f"[REALTIME] ❌ Send failed: {e}")

    async def receive_loop(self):
        async for message in self.ws:
            if not self.is_running: break
            if isinstance(message, str): continue
            
            try:
                msg = DoubaoMessage.from_bytes(message)
            except Exception as e:
                print(f"[DEBUG] Protocol Parse Error: {e}")
                continue

            if msg.serialization == SerializationBits.JSON:
                try:
                    event = json.loads(msg.payload)
                    event_type = event.get('type')
                    print(f"[DEBUG] RX JSON Event: {event_type}")
                    
                    if event_type == 'AudioInput' and event.get('state') == 'finished':
                        asr_text = event.get('asr_text') or event.get('text')
                        if asr_text: asyncio.create_task(self.on_text_received(asr_text))
                    
                    elif event_type == 'ASR' and event.get('is_final'):
                        asr_text = event.get('text')
                        if asr_text: asyncio.create_task(self.on_text_received(asr_text))
                    
                    elif event_type == 'Error' or msg.type == MsgType.Error:
                        code = event.get('code') or getattr(msg, 'error_code', 0)
                        msg_str = event.get('message') or event.get('payload_msg', {}).get('error', 'Unknown Error')
                        print(f"[REALTIME] ❌ Server Error {code}: {msg_str}")
                        
                        # Session conflict (55000001) or other terminal errors
                        if code == 55000001:
                            if hasattr(self, '_mark_turn_done'): self._mark_turn_done("session_conflict")
                except Exception as e:
                    print(f"[DEBUG] JSON Parse Error: {e}")

            elif msg.serialization == SerializationBits.Raw:
                if len(msg.payload) == 0: continue
                
                # Push ALL audio to speaker queue
                if hasattr(self, 'speaker_queue'):
                    try: 
                        self.self_speaking_mute = True
                        self.last_audio_time = time.time()
                        # [FIX] 采用 Drop-Oldest 策略防止 QueueFull 崩溃
                        try:
                            self.speaker_queue.put_nowait(msg.payload)
                        except (asyncio.queues.QueueFull, queue.Full):
                            try:
                                self.speaker_queue.get_nowait()
                                self.speaker_queue.put_nowait(msg.payload)
                            except: pass
                    except Exception as e:
                        print(f"[AUDIO] ❌ Queue push error: {e}")
                        print(f"[AUDIO] ❌ Queue push error: {e}")
            
            # Handle turn end
            if msg.event in [EventType.SessionFinished, EventType.TTSSentenceEnd]:
                 if hasattr(self, '_mark_turn_done'): self._mark_turn_done("server_done")
