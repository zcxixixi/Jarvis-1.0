"""
Hybrid Jarvis
Combines Doubao Realtime API (for speed) with Local Tools (for capability)
"""
import asyncio
import json
import gzip
import time
from typing import Optional
from jarvis_doubao_realtime import DoubaoRealtimeJarvis, DoubaoProtocol
from tools import get_all_tools
from jarvis_doubao_config import APP_ID, ACCESS_TOKEN, ws_connect_config, start_session_req, input_audio_config, output_audio_config
from audio_utils import play_boot_sound

class HybridJarvis(DoubaoRealtimeJarvis):
    def __init__(self):
        super().__init__()
        self.tools = {t.name: t for t in get_all_tools()}
        # Simplified intent mapping (in real app, use local LLM or fuzzy match)
        self.intent_keywords = {
            "天气": "get_weather",
            "几点": "get_current_time",
            "计算": "calculate",
            "开灯": "control_xiaomi_light",
            "关灯": "control_xiaomi_light",
            "打开": "control_xiaomi_light", # Added generic open
            "关闭": "control_xiaomi_light", # Added generic close
            "扫描设备": "scan_xiaomi_devices",
            "播放": "play_music",
            "放": "play_music", # Added generic play
            "播": "play_music", # Broad match for "播一首", "随便播"
            "点歌": "play_music",
            "唱": "play_music", # "唱首..."
            "来首": "play_music", # Added casual play
            "音乐": "play_music",
            "停止": "play_music", 
            "暂停": "play_music", # Added pause
        }
        
        self.music_playing = False  # Track music playback state
        self.processing_tool = False
        
        # State machine: STANDBY (default) vs ACTIVE (after wake word)
        self.ACTIVE_TIMEOUT = 15  # 用户要求 15 秒自由沟通
        self.is_active = False # Standby by default
        self.active_until = 0
        self.bot_turn_active = False # Track if bot is currently speaking for clean logs
        self.self_speaking_mute = False # ECHO FIX: Mute mic while Jarvis is speaking
        self.last_audio_time = 0  # Track when the last audio chunk was received
        
        # Initialize wake word detector
        from wake_word import get_wake_word_detector
        self.wake_detector = get_wake_word_detector()
        self.wake_detector.initialize()

    def setup_audio(self):
        """Override base setup to use config-driven parameters"""
        import pyaudio
        self.input_stream = self.p.open(
            format=input_audio_config["bit_size"],
            channels=input_audio_config["channels"],
            rate=input_audio_config["sample_rate"],
            input=True,
            frames_per_buffer=input_audio_config["chunk"]
        )
        # The user's instruction seems to redefine output_audio_config inline.
        # To make it syntactically correct and reflect the intent of using "pcm_s16le",
        # we will update the output_audio_config dictionary directly here before use.
        # This assumes the intent was to modify the configuration for this instance.
        global output_audio_config
        output_audio_config = {
            "chunk": 3200,
            "format": "pcm_s16le", # This format string is not directly used by pyaudio.open's 'format' parameter
            "channels": 1,
            "sample_rate": 24000,
            "bit_size": pyaudio.paInt16 # This is what pyaudio.open's 'format' parameter expects
        }
        self.output_stream = self.p.open(
            format=output_audio_config["bit_size"], # Use pyaudio.paInt16 from the updated config
            channels=output_audio_config["channels"],
            rate=output_audio_config["sample_rate"],
            output=True
        )
        print(f"🎙️ Audio setup complete (In: {input_audio_config['sample_rate']}Hz, Out: {output_audio_config['sample_rate']}Hz)")

    async def send_audio_loop(self):
        """
        STANDBY: Only listen for wake word. Send periodic silent packets to keep connection alive.
        ACTIVE: Upload real-time audio to cloud for 10s after wake or command.
        """
        import time
        import protocol
        
        CHUNK = 3200
        print(f"🎙️ Jarvis initialized in {'ACTIVE' if self.is_active else 'STANDBY'} mode.")
        
        last_keepalive = 0
        SILENT_SAMPLE = b'\x00' * 3200 # Constant silent frame for keepalive
        
        while True:
            try:
                # 1. Read Mic Data
                data = self.input_stream.read(CHUNK, exception_on_overflow=False)
                now = time.time()

                # 2. Local Wake Word Detection (Always running)
                if self.wake_detector.process_audio(data):
                    # IMMEDIATE DUCK to maximize listening for the follow-up
                    from audio_utils import lower_music_volume
                    lower_music_volume()
                    
                    print("\n🎤 'JARVIS' detected!")
                    
                    if not self.is_active:
                        # Full wake-up: sound, music stop, volume duck
                        await self.stop_music_and_resume() 
                        self.is_active = True
                        print(f"🌟 Mode: ACTIVE")
                    else:
                        # Already active: just reset timer and acknowledge softly
                        print(f"✨ Session extended")
                        # Ensure volume is ducked if it wasn't
                        from audio_utils import lower_music_volume
                        lower_music_volume()
                        # If a bot was speaking, stop it
                        if self.bot_turn_active or self.self_speaking_mute:
                             print("🛑 Interrupting speech...")
                             self.self_speaking_mute = False
                             self.bot_turn_active = False
                    
                    self.active_until = now + self.ACTIVE_TIMEOUT
                    continue # Skip sending this frame

                # CRITICAL FIX: Auto-unmute mic after Jarvis stops speaking (1 second silence)
                # Only do this in ACTIVE mode - in STANDBY we don't need mic
                if self.is_active and self.self_speaking_mute and self.last_audio_time > 0:
                    if now - self.last_audio_time > 1.0:
                        print("\n[已恢复收音] Mic auto-resumed after speech pause")
                        self.self_speaking_mute = False
                        self.bot_turn_active = False
                        self.last_audio_time = 0
                        # Reset timeout for continuous conversation
                        self.active_until = now + self.ACTIVE_TIMEOUT

                # 3. State Management
                if self.is_active:
                    # Check for timeout
                    if now > self.active_until:
                        self.is_active = False
                        print("\n💤 Timeout - Returning to STANDBY mode.")
                        # Restore volume to original level so music keeps playing nicely in background
                        from audio_utils import restore_music_volume
                        restore_music_volume()
                        # Ensure mute flags are reset
                        self.self_speaking_mute = False
                        self.bot_turn_active = False
                
                # 4. Data Sending Logic (ECHO FIX: check self_speaking_mute)
                if self.is_active:
                    if not self.self_speaking_mute:
                        # ACTIVE: Send real mic data
                        await self._send_raw_audio(data)
                    else:
                        # ECHO PREVENTED: Send silence instead of mic data
                        await self._send_raw_audio(SILENT_SAMPLE[:320])
                else:
                    # STANDBY: Only send keepalive every 5s to prevent timeout
                    if now - last_keepalive > 5.0:
                        # Send a very short silent packet
                        await self._send_raw_audio(SILENT_SAMPLE[:320]) # 20ms silence
                        last_keepalive = now
                        print(".", end="", flush=True) # Heartbeat indicator
                
                await asyncio.sleep(0.01)
                
            except Exception as e:
                print(f"Audio loop error: {e}")
                await asyncio.sleep(0.5)

    async def _send_raw_audio(self, data):
        """Helper to package and send audio according to Doubao protocol"""
        import protocol
        import gzip
        
        req = bytearray(protocol.generate_header(
            message_type=protocol.CLIENT_AUDIO_ONLY_REQUEST,
            serial_method=protocol.NO_SERIALIZATION
        ))
        # Audio Event ID 200
        req.extend((200).to_bytes(4, 'big'))
        session_bytes = self.session_id.encode('utf-8')
        # Official client: unsigned 4-byte big endian for length in task_request
        req.extend(len(session_bytes).to_bytes(4, 'big'))
        req.extend(session_bytes)
        
        payload_bytes = gzip.compress(data)
        req.extend(len(payload_bytes).to_bytes(4, 'big'))
        req.extend(payload_bytes)
        
        await self.ws.send(req)

    async def stop_music_and_resume(self):
        """Helper to stop music (temporarily or fully) and resume normal listening"""
        from audio_utils import play_wake_sound, lower_music_volume
        
        # 1. Duck volume immediately so we can hear the next user command
        lower_music_volume()
        
        # 2. Play wake sound
        play_wake_sound()
        
        # 3. Stop music (We usually keep it stopped to avoid echo in long turns, 
        # but the ducking already happened for the 'ding')
        local_tool = self.tools.get("play_music")
        cloud_tool = self.tools.get("play_music_cloud")
        if local_tool: await local_tool.execute(action="stop")
        if cloud_tool: await cloud_tool.execute(action="stop")
        
        self.music_playing = False
        self.self_speaking_mute = False # Ensure mic is open
        self.bot_turn_active = False    # Ensure we can speak cleanly
        print("🔊 Music stopped & Volume ducked - Jarvis is ready.")

    async def keyboard_input_loop(self):
        """Listen for keyboard input and send as text query"""
        import sys
        from asyncio import get_event_loop
        
        loop = get_event_loop()
        reader = asyncio.StreamReader()
        protocol_reader = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol_reader, sys.stdin)
        
        print("⌨️  键盘监听已开启 - 直接输入文字即可...")
        
        while True:
            try:
                # Async read from stdin
                line = await reader.readline()
                if not line:
                    break
                    
                text = line.decode('utf-8').strip()
                if not text:
                    continue
                
                # Special Handle: 'Jarvis' or '贾维斯' via keyboard acts as wake/stop
                sleep_keywords = ["退下", "休息", "闭嘴", "可以了", "再见", "拜拜", "退出", "休眠"]
                
                if text.lower() == "jarvis" or text == "贾维斯":
                    print(f"\n⌨️ '{text}' typed! Waking up...")
                    await self.stop_music_and_resume()
                    self.is_active = True
                    self.active_until = time.time() + self.ACTIVE_TIMEOUT
                    # Lower volume for listening
                    from audio_utils import lower_music_volume
                    lower_music_volume()
                    continue
                
                elif any(kw in text for kw in sleep_keywords):
                    print(f"\n⌨️ '{text}' typed! Sleeping...")
                    self.is_active = False
                    self.active_until = 0
                    # For keyboard, we need a manual confirm
                    await self.send_text_query(f"System: 用户命令你休息。请仅用一个词（如“遵命”或“好”）礼貌回复。")
                    # Restore volume for standby/music
                    from audio_utils import restore_music_volume
                    restore_music_volume()
                    continue
                    
                print(f"📝 键盘输入: {text}")
                
                # Typing any command also wakes Jarvis up
                self.is_active = True
                self.active_until = time.time() + self.ACTIVE_TIMEOUT
                
                # Check tools locally first (Optimization)
                if any(k in text for k in self.intent_keywords):
                    await self.check_and_run_tool(text)
                else:
                    # Send to Doubao for normal chat (will reply with voice)
                    await self.send_text_query(text)
                    
            except Exception as e:
                print(f"Keyboard error: {e}")
                break

    async def connect(self):
        import ssl
        import websockets
        import protocol # Import Protocol
        
        # Use config from jarvis_doubao_config.py
        headers = ws_connect_config["headers"]
        ws_url = ws_connect_config["base_url"]
        
        print(f"🤖 Connecting to Doubao...")
        
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            async with websockets.connect(ws_url, additional_headers=headers, ssl=ssl_ctx, ping_interval=None) as ws:
                self.ws = ws
                
                # Logid check
                logid = getattr(ws, 'response_headers', {}).get("X-Tt-Logid", "N/A")
                print(f"✅ Connected! LogID: {logid}")
                
                # Reset state flags on fresh connection
                self.self_speaking_mute = False
                self.bot_turn_active = False
                self.processing_tool = False
                
                # 1. StartConnection (Event 1)
                await self.send_start_connection()
                
                # 2. StartSession (Event 100)
                await self.send_start_session()
                
                # 3. Audio
                self.setup_audio()
                print("🎙️ Jarvis is alive. Speak or Type!")
                
                # Run everything concurrently
                await asyncio.gather(
                    self.receive_loop(),
                    self.send_audio_loop(),
                    self.keyboard_input_loop()
                )
                
        except Exception as e:
            print(f"❌ Error: {e}")

    async def send_start_connection(self):
        import protocol
        
        req = bytearray(protocol.generate_header())
        req.extend((1).to_bytes(4, 'big'))
        
        # Payload {}
        payload_bytes = gzip.compress(json.dumps({}).encode('utf-8'))
        req.extend(len(payload_bytes).to_bytes(4, 'big'))
        req.extend(payload_bytes)
        
        await self.ws.send(req)
        resp = await self.ws.recv()
        # Parse?
        print(f"   StartConnection OK")

    async def send_start_session(self):
        import protocol
        
        # Merge config with dynamic updates
        config_payload = start_session_req.copy()
        
        # Ensure we ask for standard PCM (Explicitly S16LE to avoid noise)
        config_payload["tts"]["audio_config"]["format"] = "pcm_s16le" 
        # config_payload["dialog"]["extra"]["input_mod"] = "hybrid" # Try hybrid if supported, or stick to "audio"
        
        print(f"⚙️ Session Config: {json.dumps(config_payload, ensure_ascii=False)[:200]}...")
        
        req = bytearray(protocol.generate_header())
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
        # Parse start session response to check for errors
        parsed = protocol.parse_response(resp)
        print(f"   StartSession Response: {parsed}")


    async def receive_loop(self):
        """Receive messages from Doubao and process them"""
        import protocol
        import gzip
        import json
        
        print("📥 Receive loop started.")
        
        try:
            async for message in self.ws:
                if isinstance(message, str):
                    continue
                    
                # Use official protocol parser for robustness
                # It handles version, compression, and serialization
                result = protocol.parse_response(message)
                
                # 1. Update active status on ANY server traffic
                if self.is_active:
                    self.active_until = time.time() + self.ACTIVE_TIMEOUT

                # 2. Extract payload and type
                payload = result.get('payload_msg')
                if payload is None:
                    continue
                
                serialization_type = (message[2] >> 4)
                
                # --- Case A: Audio (Binary) ---
                if serialization_type == protocol.NO_SERIALIZATION:
                    if not self.processing_tool and isinstance(payload, bytes):
                        # ECHO FIX: Mute mic while we are pushing audio out
                        self.self_speaking_mute = True
                        self.last_audio_time = time.time()  # Track last audio chunk
                        
                        try:
                            self.output_stream.write(payload, exception_on_underflow=False)
                        except Exception as e:
                            if "35" in str(e):
                                pass
                            else:
                                print(f"\n⚠️ Audio Playback Error: {e}")
                        
                        if time.time() % 5 < 0.1:
                             print(".", end="", flush=True)
                
                # --- FALLBACK: Unmute mic if no audio for 1 second ---
                if self.self_speaking_mute and self.last_audio_time > 0:
                    if time.time() - self.last_audio_time > 1.0:
                        print("\n[已恢复收音] Mic auto-resumed after speech pause")
                        self.self_speaking_mute = False
                        self.bot_turn_active = False
                        self.last_audio_time = 0
                        # Reset timeout for continuous conversation
                        self.active_until = time.time() + self.ACTIVE_TIMEOUT
                
                # --- Case B: JSON Events ---
                elif serialization_type == protocol.JSON:
                    event = payload
                    if not isinstance(event, dict):
                        continue
                        
                    # Filter voice activity noise
                    if event.get('type') not in ['audio', 'speech_segments']:
                        # print(f"\n📦 Event: {json.dumps(event, ensure_ascii=False)[:200]}")
                        pass
                    
                    if not self.is_active:
                         # Even if in standby, we might get late events or a "Confirm Retreat" TTS
                         # But normally we don't trigger tools or text logic in standby
                         pass

                    user_text = None
                    bot_text = None
                    
                    # 1. User ASR (Transcription)
                    if event.get('type') == 'conversation.item.input_audio_transcription.completed':
                        user_text = event.get('transcript', '')
                    elif 'extra' in event and isinstance(event['extra'], dict):
                        # Use finalized text from extra if endpoint reached
                        if event['extra'].get('endpoint'):
                             user_text = event['extra'].get('origin_text')
                    elif 'result' in event and isinstance(event['result'], dict):
                        # Catch-all for other ASR styles
                        user_text = event['result'].get('text')
                    
                    # 2. Bot Response (TTS Text)
                    if 'text' in event:
                        bot_text = event['text']
                    elif 'content' in event:
                        bot_text = event['content']
                    
                    # Tool Activation Logic
                    if user_text:
                        print(f"\n🎧 User Speech: {user_text}")
                        # Keep active mode alive whenever user speaks
                        self.is_active = True
                        self.active_until = time.time() + self.ACTIVE_TIMEOUT
                        
                        await self.check_and_run_tool(user_text)
                    
                    if bot_text:
                        if not self.bot_turn_active:
                            print(f"\n🗣️ Jarvis: ", end="", flush=True)
                            self.bot_turn_active = True
                        print(bot_text, end="", flush=True)
                        # CRITICAL: Also reset timeout during speech to prevent mid-speech dropout
                        self.active_until = time.time() + self.ACTIVE_TIMEOUT
                    
                    # End of turn detection (Reset timeout and mic)
                    # Also check for 'finished' keyword in event type to catch more variations
                    event_type = event.get('type', '')
                    is_turn_end = 'finished' in event_type or 'done' in event_type or event.get('done') == True
                    
                    # DEBUG: Log event types to understand the protocol
                    if event_type and event_type not in ['audio', 'speech_segments', '']:
                        print(f"\n[DEBUG EVENT] type={event_type}", end="", flush=True)
                    
                    if is_turn_end:
                         if self.bot_turn_active:
                              print("\n[Turn Finished]")
                              self.bot_turn_active = False
                              self.self_speaking_mute = False
                              self.active_until = time.time() + self.ACTIVE_TIMEOUT
                              print(f"⏱️ Jarvis finished. Listen window: 15s remaining.")
                        
        except Exception as e:
             print(f"\n❌ Receive loop error: {e}")
             import traceback
             traceback.print_exc()

    async def send_text_query(self, text: str):
        """Send text query to Doubao (triggers TTS response)"""
        import protocol
        import time
        print(f"📤 Sending text: {text}")
        
        # Keep active mode alive while sending
        self.is_active = True
        self.active_until = time.time() + self.ACTIVE_TIMEOUT
        
        payload = {"content": text}
        payload_bytes = gzip.compress(json.dumps(payload).encode('utf-8'))
        
        # Use CLIENT_FULL_REQUEST for text queries (standard for binary protocols)
        req = bytearray(protocol.generate_header(
            message_type=protocol.CLIENT_FULL_REQUEST,
            serial_method=protocol.JSON
        ))
        req.extend((501).to_bytes(4, 'big')) # Chat Text Query
        
        session_bytes = self.session_id.encode('utf-8')
        req.extend(len(session_bytes).to_bytes(4, 'big'))
        req.extend(session_bytes)
        
        req.extend(len(payload_bytes).to_bytes(4, 'big'))
        req.extend(payload_bytes)
        
        await self.ws.send(req)

    async def check_and_run_tool(self, text: str):
        """Check text for keywords and run tools"""
        import re
        import random
        import time
        
        # Extend active timeout on any interaction
        self.is_active = True
        self.active_until = time.time() + self.ACTIVE_TIMEOUT
        
        # Priority check for music stop/pause (Must match exactly to avoid searching for 'pause' song)
        stop_keywords = ["停止", "暂停", "关掉", "断开", "别播了", "切断"]
        if any(kw in text for kw in stop_keywords):
            print(f"🛑 Local Stop Triggered: {text}")
            # Stop both local and cloud music
            local_tool = self.tools.get("play_music")
            cloud_tool = self.tools.get("play_music_cloud")
            
            if local_tool: await local_tool.execute(action="stop")
            if cloud_tool: await cloud_tool.execute(action="stop")
            
            self.music_playing = False  
            self.self_speaking_mute = False 
            print("🎤 Mic resumed (music stopped)")
            return

        # Priority check for Sleep/Standby
        sleep_keywords = ["退下", "休息", "闭嘴", "可以了", "再见", "拜拜", "退出", "休眠"]
        if any(kw in text for kw in sleep_keywords):
            if not self.is_active: return # Already standby
            
            print(f"\n💤 Sleep command detected: {text}")
            self.is_active = False
            self.active_until = 0
            
            # NEW: We rely on the cloud's natural response to the voice "退下"
            # We only send a manual confirm if it's the keyboard (since there's no audio context)
            # If from ASR, the cloud is likely already saying "好的" or similar.
            # We only send a system prompt if we want to FORCE a specific Jarvis response.
            # Removing it here to prevent double response.
            
            from audio_utils import restore_music_volume
            restore_music_volume()
            return

        for keyword, tool_name in self.intent_keywords.items():
            if keyword in text:
                print(f"\n⚡ Detected Intent: {tool_name}")
                self.processing_tool = True
                
                # Execute Tool
                tool = self.tools.get(tool_name)
                
                try:
                    # --- Intelligent Parameter Extraction ---
                    if tool_name == "get_weather":
                        # Cleaning: remove common stopwords to isolate city
                        stopwords = ["天气", "查询", "的", "今天", "怎么样", "现在", "目前", "帮我", "看看", "查一下"]
                        city = text
                        for w in stopwords:
                            city = city.replace(w, "")
                        city = city.strip()
                        
                        if not city: city = "Beijing" # Fallback
                        print(f"📍 Extracted City: {city}")
                        result = await tool.execute(city=city) 
                        
                    elif tool_name == "control_xiaomi_light":
                         # Extract action
                         if "开" in text: action="on"
                         elif "关" in text: action="off"
                         else: action="status"
                         result = await tool.execute(ip="192.168.1.x", token="xxx", action=action)
                    
                    elif tool_name == "play_music":
                        if any(kw in text for kw in ["停止", "暂停", "关掉", "结束"]):
                            result = await tool.execute(action="stop")
                        elif "列表" in text:
                            result = await tool.execute(action="list")
                        else:
                            # Search/Play logic
                            # 1. Clean up "play" keywords
                            stopwords = ["播放", "来首", "音乐", "放一首", "听", "我要", "给我", "的", "歌", "播", "放", "为您", "好的", "一首", "点一个", "点一首", "请听"]
                            query = text
                            
                            # Extract content from brackets if present (e.g. 《彩虹》)
                            bracketed = re.search(r"《(.+?)》", text)
                            if bracketed:
                                query = bracketed.group(1)
                            else:
                                for w in stopwords:
                                    query = query.replace(w, "")
                            
                            query = query.strip()
                            # 2. Logic: If query is empty or generic (e.g. "随便"), play ANY song
                            # If query exists, try to find it.
                            if not query or query in ["随便", "好听", "背景", "复习"] or len(query) < 1:
                                # List all music first
                                all_music = tool._scan_music()
                                if all_music:
                                    # Pick one randomly or first
                                    import os
                                    target = os.path.basename(random.choice(all_music))
                                    print(f"🎲 Random play: {target}")
                                    result = await tool.execute(action="play", query=target)
                                else:
                                    # Fallback to Cloud (Migu)
                                    # We ask for "Light Music" equivalent if random fails
                                    cloud_tool = self.tools.get("play_music_cloud")
                                    result = await cloud_tool.execute(action="play", query="轻音乐")
                            else:
                                # Specific search - Local First
                                local_res = await tool.execute(action="play", query=query)
                                
                                if "❌" in local_res or "未找到" in local_res:
                                    print(f"🏠 Local miss. Trying Cloud Music (Migu) for: {query}")
                                    cloud_tool = self.tools.get("play_music_cloud")
                                    result = await cloud_tool.execute(action="play", query=query)
                                else:
                                    result = local_res
                            
                            # NEW: Mute mic during music playback and restore volume
                            if "正在播放" in result:
                                self.music_playing = True
                                self.is_active = False # Back to standby while playing
                                from audio_utils import restore_music_volume
                                restore_music_volume()
                                print("🔇 Mic muted (music playing) - Type '停止' to interrupt")
                        
                    elif tool_name == "calculate":
                        result = await tool.execute(expression="1+1")
                        
                    elif tool_name == "scan_xiaomi_devices":
                        result = await tool.execute()

                    else:
                        result = await tool.execute()
                        
                except Exception as e:
                    result = f"Error: {e}"

                print(f"🔧 Tool Result: {result}")
                
                # Send result back to Doubao to speak
                # REDUNDANCY FIX: Music tools already have natural ASR confirmation.
                # Do NOT send system prompt for simple music playback to avoid double-talk.
                if tool_name in ["play_music", "play_music_cloud"]:
                    self.processing_tool = False
                    return 
                
                prompt = f"System: 用户刚才触发了工具。执行结果是：{result}。请用自然语言告诉用户这个结果。"
                await self.send_text_query(prompt)
                
                self.processing_tool = False
                return

if __name__ == "__main__":
    # Play boot sequence once
    play_boot_sound()
    
    jarvis = HybridJarvis()
    
    # Robust Reconnection Loop
    RETRY_DELAY = 1
    MAX_RETRIES = 5
    
    while True:
        try:
            print(f"\n🚀 Starting Jarvis (Auto-Reconnect Mode)...")
            asyncio.run(jarvis.connect())
            
            # If connect returns cleanly (user exit), break loop
            if not jarvis.is_running:
                break
                
        except KeyboardInterrupt:
            print("\n👋 User stopped Jarvis.")
            break
        except Exception as e:
            print(f"\n⚠️ Connection lost or crashed: {e}")
            print(f"🔄 Reconnecting in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
            RETRY_DELAY = min(RETRY_DELAY * 2, 30) # Exponential backoff max 30s
            
            # Reset instance state if needed
            jarvis = HybridJarvis()

