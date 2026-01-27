"""
Hybrid Jarvis
Combines Doubao Realtime API (for speed) with Local Tools (for capability)
"""
print("🚀 [TOP-LEVEL] Hybrid Jarvis script starting...", flush=True)
import asyncio
import json
import gzip
import time
import re
import os
import numpy as np
import queue
from typing import Optional
print("🚀 [TOP-LEVEL] Imports complete", flush=True)
from jarvis_assistant.services.doubao.websocket import DoubaoRealtimeJarvis, DoubaoProtocol
from jarvis_assistant.services.tools import get_all_tools
from jarvis_assistant.config.doubao_config import APP_ID, ACCESS_TOKEN, ws_connect_config, start_session_req, input_audio_config, output_audio_config, MICROPHONE_DEVICE_INDEX, INPUT_HARDWARE_SAMPLE_RATE, SPEAKER_DEVICE_INDEX
from jarvis_assistant.utils.audio_utils import play_boot_sound
from jarvis_assistant.services.audio.aec import get_aec
import audioop # For high-quality resampling ratecv

class HybridJarvis(DoubaoRealtimeJarvis):
    async def on_text_received(self, text: str):
        """
        [Slow Brain Hook]
        Called when Realtime API recognizes text but (presumably) didn't trigger a regex action.
        We pass this to Agent Core for complex planning.
        """
        print(f"🧠 Slow Brain (Cognitive) processing: {text}")
        
        # 1. Ask Brain to plan & execute
        # This will query Doubao HTTP (if configured) or just conversation
        response_text = await self.brain.run(text)
        
        # 2. Speak the result using Doubao Realtime TTS
        # We need access to the session to send TTS request
        # self.client is the RealtimeDialogClient
        if hasattr(self, 'client') and self.client:
             print(f"🗣️ Speaking Brain Response: {response_text}")
             await self.client.chat_tts_text(
                 is_user_querying=False,
                 start=True,
                 end=True,
                 content=response_text
             )
        else:
             print(f"⚠️ Cannot speak response (Client not ready): {response_text}")

    def __init__(self):
        print("🔧 HybridJarvis: Initializing...", flush=True)
        super().__init__()
        print("🔧 HybridJarvis: Base class initialized", flush=True)
        self.tools = {t.name: t for t in get_all_tools()}
        # Simplified intent mapping (in real app, use local LLM or fuzzy match)
        self.intent_keywords = {
            "天气": "get_weather",
            "几点": "get_current_time",
            "计算": "calculate",
            "搜索": "web_search",
            "开灯": "control_xiaomi_light",
            "关灯": "control_xiaomi_light",
            "打开": "control_xiaomi_light", 
            "关闭": "control_xiaomi_light", 
            "电灯": "control_xiaomi_light",
            "扫描设备": "scan_xiaomi_devices",
            "播放": "play_music",
            "放个": "play_music",
            "放首": "play_music",
            "放点": "play_music",
            "播一": "play_music",
            "点歌": "play_music",
            "听歌": "play_music",
            "听点": "play_music",
            "想听": "play_music",
            "我要听": "play_music",
            "音乐": "play_music",
            "广播": "play_music",
            "停止": "play_music", 
            "别播": "play_music",
            "别放": "play_music",
            "关闭音乐": "play_music",
            "暂停": "play_music",
        }
        
        self.music_playing = False  # Track music playback state
        self.processing_tool = False
        self.skip_cloud_response = False  # NEW: Skip Doubao's TTS while local tool is executing
        self.text_send_queue = None
        
        self.text_only = os.environ.get("JARVIS_TEXT_ONLY", "0") == "1"
        if self.text_only:
            print("⌨️  Text-only mode enabled (keyboard input, no mic)")
        self.local_tts_enabled = self.text_only
        self._bot_text_buffer = []
        self._tts_flush_task = None

        # Turn-level gating to prevent out-of-order responses
        self.pending_response = False
        self.turn_done = asyncio.Event()
        self.turn_done.set()
        self.turn_timeout_task = None
        self.turn_timeout_seconds = 20
        self._receive_loop_task = None

        # [NEW] Initialize Cognitive Brain (Agent Core)
        from jarvis_assistant.core.agent import JarvisAgent
        self.brain = JarvisAgent()
        print("🧠 HybridJarvis: Cognitive Brain Connected")
        
        # State machine: STANDBY (default) vs ACTIVE (after wake word)
        self.ACTIVE_TIMEOUT = 15  # 用户要求 15 秒自由沟通
        self.is_active = False # Standby by default
        self.active_until = 0
        self.bot_turn_active = False # Track if bot is currently speaking for clean logs
        self.self_speaking_mute = False # ECHO FIX: Mute mic while Jarvis is speaking
        self.last_audio_time = 0  # Track when the last audio chunk was received
        self.discard_incoming_audio = False # INTERRUPT FIX: Ignore trailing audio after wake
        
        # Initialize wake word detector (skip in text-only mode)
        if not self.text_only:
            from jarvis_assistant.services.audio.wake_word import get_wake_word_detector
            self.wake_detector = get_wake_word_detector()
            self.wake_detector.initialize()
        else:
            self.wake_detector = None
        
        # Initialize AEC
        print("🔧 HybridJarvis: Loading AEC...")
        self.aec = get_aec(sample_rate=16000)
        print("🔧 HybridJarvis: AEC Loaded")
        
        # [NEW] 添加重采样状态变量
        self.mic_resample_state = None  # 用于麦克风 48k -> 16k
        self.ref_resample_state = None  # 用于参考信号 24k -> 16k

    def _transition_to_active(self, reason="unknown"):
        """Log state change to ACTIVE"""
        if not self.is_active:
            print(f"\n🔄 STATE CHANGE: STANDBY -> ACTIVE (Reason: {reason})")
            self.is_active = True
        self.active_until = time.time() + self.ACTIVE_TIMEOUT

    def _transition_to_standby(self, reason="unknown"):
        """Log state change to STANDBY"""
        if self.is_active:
            print(f"\n🔄 STATE CHANGE: ACTIVE -> STANDBY (Reason: {reason})")
            self.is_active = False
            from jarvis_assistant.utils.audio_utils import restore_music_volume
            restore_music_volume()
            self.self_speaking_mute = False
            self.bot_turn_active = False

    def find_mic_index(self):
        """Dynamically find the USB microphone index by name"""
        import pyaudio
        target_name = "USB Audio" # Matches "(LCS) USB Audio Device"
        for i in range(self.p.get_device_count()):
            try:
                info = self.p.get_device_info_by_index(i)
                name = info.get("name", "")
                if target_name in name:
                    print(f"🎯 Jarvis: Found USB Mic at Index {i}")
                    return i
            except:
                continue
        print(f"⚠️  Jarvis: Target mic '{target_name}' not found. Using config fallback: {MICROPHONE_DEVICE_INDEX}")
        return MICROPHONE_DEVICE_INDEX

    def setup_audio(self):
        """Override base setup to use config-driven parameters with dynamic discovery"""
        import pyaudio
        
        mic_index = self.find_mic_index()
        print(f"🎙️ Jarvis: Opening Mic (Index {mic_index}) at {INPUT_HARDWARE_SAMPLE_RATE}Hz...")
        
        try:
            self.input_stream = self.p.open(
                format=input_audio_config["bit_size"],
                channels=input_audio_config["channels"],
                rate=INPUT_HARDWARE_SAMPLE_RATE,
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=input_audio_config["chunk"] * 3
            )
        except Exception as e:
            print(f"❌ Jarvis: Failed to open mic at Index {mic_index}: {e}")
            # Try index 1 as a common fallback for USB mics on Pi
            for fallback in [1, 0, 2]:
                if fallback == mic_index: continue
                try:
                    print(f"🔄 Jarvis: Trying fallback Index {fallback}...")
                    self.input_stream = self.p.open(
                        format=input_audio_config["bit_size"],
                        channels=input_audio_config["channels"],
                        rate=INPUT_HARDWARE_SAMPLE_RATE,
                        input=True,
                        input_device_index=fallback,
                        frames_per_buffer=input_audio_config["chunk"] * 3
                    )
                    print(f"✅ Jarvis: Success with Index {fallback}!")
                    break
                except: continue
            else:
                raise e

        # Standard output setup
        # Use SPEAKER_DEVICE_INDEX from config (typically 2 on Mac)
        self.output_stream = self.p.open(
            format=output_audio_config["bit_size"],
            channels=output_audio_config["channels"],
            rate=output_audio_config["sample_rate"],
            output=True,
            output_device_index=SPEAKER_DEVICE_INDEX
        )
        print(f"🎙️ Jarvis: Audio setup complete (In: {input_audio_config['sample_rate']}Hz, Out: {output_audio_config['sample_rate']}Hz, Spk: {SPEAKER_DEVICE_INDEX})", flush=True)
        
        # [NEW] Speaker Thread (Jitter Buffer)
        import queue
        import threading
        # Bounded queue to prevent unbounded latency (50 chunks = ~1s buffer)
        self.speaker_queue = queue.Queue(maxsize=50) 
        self.speaker_thread = threading.Thread(target=self._speaker_worker, daemon=True)
        self.speaker_thread.start()
        print(f"✅ Speaker Thread Started (Jitter Buffer Max: 50)")

    def setup_output_audio(self):
        """Setup speaker output only (text-only mode)."""
        import pyaudio

        self.output_stream = self.p.open(
            format=output_audio_config["bit_size"],
            channels=output_audio_config["channels"],
            rate=output_audio_config["sample_rate"],
            output=True,
            output_device_index=SPEAKER_DEVICE_INDEX
        )
        print(
            "🎙️ Jarvis: Audio output ready (Out: "
            f"{output_audio_config['sample_rate']}Hz, Spk: {SPEAKER_DEVICE_INDEX})",
            flush=True
        )

        import queue
        import threading
        self.speaker_queue = queue.Queue(maxsize=50)
        self.speaker_thread = threading.Thread(target=self._speaker_worker, daemon=True)
        self.speaker_thread.start()
        print("✅ Speaker Thread Started (Jitter Buffer Max: 50)")

    def _mic_reader_thread(self, loop, audio_queue, chunk_size):
        """
        [专用线程] 持续从麦克风读取数据，绝不通过 await 暂停，确保无丢帧。
        """
        import time
        print("🧵 [THREAD] Mic Reader Thread starting...", flush=True)
        while self.is_running:
            try:
                # 这是一个阻塞调用，但因为它在独立线程里，所以没关系！
                # 它可以完美地按硬件时钟节奏运行
                data = self.input_stream.read(chunk_size, exception_on_overflow=False)
                
                # 线程安全地将数据放入 asyncio 主循环的队列中
                loop.call_soon_threadsafe(audio_queue.put_nowait, data)
            except OSError as e:
                # 忽略一些良性的溢出错误，或者是设备临时忙
                if "Input overflowed" in str(e):
                    pass
                elif "Stream closed" in str(e) or "Input/output error" in str(e):
                    print(f"❌ Mic Critical Error: {e} - Stream lost, restart required.")
                    time.sleep(1.0)
                else:
                    print(f"⚠️ Mic Read Warning: {e}")
                    time.sleep(0.01)
            except Exception as e:
                print(f"❌ Mic Thread Critical: {e}")
                time.sleep(0.1)


    def _speaker_worker(self):
        """
        [专用播放线程] 充当 Jitter Buffer，平滑网络波动，防止阻塞主循环
        消费者：负责从队列获取 -> 写入声卡 -> 喂给 AEC
        """
        import audioop
        
        while self.is_running:
            try:
                # 阻塞等待音频数据 (timeout allows checking is_running)
                data = self.speaker_queue.get(timeout=1.0)
                if data is None: continue 
                
                # [LATENCY MEASUREMENT]
                start_write = time.time()
                q_size = self.speaker_queue.qsize()
                
                # 在独立线程中写入声卡，卡住也不影响主程序
                self.output_stream.write(data, exception_on_underflow=False)
                
                latency = (time.time() - start_write) * 1000
                if latency > 100: # Log spikes > 100ms
                    print(f"⚠️ [AUDIO] Hardware write spike: {latency:.1f}ms (Queue depth: {q_size})")
                
                # --- AEC Reference Feeding (Moved here for accurate timing) ---
                # Resample 24k (Doubao) -> 16k (AEC)
                try:
                    ref_chunk, self.ref_resample_state = audioop.ratecv(
                        data, 
                        2, 
                        1, 
                        24000, 
                        16000, 
                        self.ref_resample_state
                    )
                    self.aec.feed_reference(ref_chunk)
                except Exception as e:
                    print(f"Ref resample error: {e}")
                # -----------------------------
                
                self.speaker_queue.task_done()
            except:
                continue

    async def send_audio_loop(self):
        """
        改进后的非阻塞音频循环：使用队列缓冲，彻底消除卡顿和丢帧。
        """
        import time
        import threading
        import jarvis_assistant.services.doubao.protocol as protocol
        import websockets
        
        print(f"🎙️ Jarvis initialized in {'ACTIVE' if self.is_active else 'STANDBY'} mode.", flush=True)
        
        # SILENT_SAMPLE dynamic generation moved inside loop for robustness
        
        # 1. 准备队列和专用线程
        self.audio_queue = asyncio.Queue(maxsize=500) # 缓冲约10秒音频，防止由于网络卡顿导致的崩坏
        hardware_chunk = input_audio_config["chunk"] * 3
        
        loop = asyncio.get_running_loop()
        
        # 启动“吸音”线程
        self.reader_thread = threading.Thread(
            target=self._mic_reader_thread, 
            args=(loop, self.audio_queue, hardware_chunk),
            daemon=True
        )
        self.reader_thread.start()
        print("✅ Audio Reader Thread Started (Zero-Latency Mode)")

        while True:
            try:
                # 2. 从队列获取数据 (纯异步等待，消耗极低)
                raw_data_48k = await self.audio_queue.get()
                
                # Resample 48k -> 16k using polyphase filtering (High Quality)
                # ratecv(fragment, width, nchannels, inrate, outrate, state, weightA, weightB)
                raw_data, self.mic_resample_state = audioop.ratecv(
                    raw_data_48k, 
                    2,  # width (16-bit = 2 bytes)
                    1,  # channels
                    INPUT_HARDWARE_SAMPLE_RATE,  # Use config variable (e.g. 48000)
                    16000, 
                    self.mic_resample_state
                )
                
                # Dynamic silence generation to handle clock drift/resample jitter
                current_chunk_size = len(raw_data)
                silent_chunk = b'\x00' * current_chunk_size
                
                pcm_16k = np.frombuffer(raw_data, dtype=np.int16)

                # --- AEC Processing ---
                data = self.aec.cancel_echo(raw_data)
                
                now = time.time()
                
                # Audio level monitoring (print every ~2 seconds if active)
                if int(now) % 2 == 0 and now - getattr(self, '_last_level_time', 0) > 1.0:
                    self._last_level_time = now
                    rms = np.sqrt(np.mean(pcm_16k.astype(np.float32)**2))
                    if rms > 10: 
                        print(f"[MIC INFO] Level RMS: {rms:.1f}")

                # --- WAKE WORD GAIN BOOST (Increase to 10x for sensitivity) ---
                try:
                    wake_pcm = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                    wake_pcm = np.clip(wake_pcm * 10.0, -32768, 32767).astype(np.int16)
                    data_for_wake = wake_pcm.tobytes()
                except:
                    data_for_wake = data

                # 2. Local Wake Word Detection
                # SENSITIVITY UP: Lowering threshold during music (0.85 -> 0.70)
                current_threshold = 0.70 if self.music_playing else None
                
                if self.wake_detector.process_audio(data_for_wake, threshold=current_threshold):
                    if self.processing_tool:
                        continue
                    
                    wake_cooldown = getattr(self, '_last_wake_time', 0)
                    if now - wake_cooldown < 2.0:
                        continue 
                    self._last_wake_time = now
                    
                    from jarvis_assistant.utils.audio_utils import play_wake_sound
                    
                    # 1. Play sound and get its length
                    sound_duration = play_wake_sound()
                    
                    # 2. Stop music & reset in background
                    await self.stop_music_and_resume() 
                    await self.send_reset_signal()
                    if self.aec: self.aec.reset()
                    
                    # 3. SET DYNAMIC IGNORE WINDOWS
                    # Wait for the sound to finish + 0.2s margin
                    ignore_period = sound_duration + 0.2
                    self._ignore_audio_until = time.time() + ignore_period
                    self.ignore_server_audio_until = time.time() + (ignore_period + 1.0)
                    self.discard_incoming_audio = True
                    
                    # Increase wake_cooldown to prevent double triggers during the long sound
                    self._last_wake_time = time.time() + (sound_duration * 0.5) 
                    
                    print(f"\n🎤 Local Wake: 'JARVIS' detected! Sound length: {sound_duration:.2f}s")
                    self._transition_to_active(reason="wake_word")
                    continue

                # Auto-unmute mic after Jarvis stops speaking
                if self.self_speaking_mute and self.last_audio_time > 0:
                    if now - self.last_audio_time > 1.0:
                        self.self_speaking_mute = False
                        self.bot_turn_active = False
                        self.last_audio_time = 0
                        self._transition_to_active(reason="unmute_auto")

                # 3. State Management
                if self.is_active:
                    if now > self.active_until:
                        self._transition_to_standby(reason="timeout")
                
                # 4. Data Sending Logic
                # 判断当前是否正在播放（队列不为空 OR 标志位）
                is_speaking_now = not self.speaker_queue.empty() or self.self_speaking_mute
                
                if self.is_active and not is_speaking_now:
                    # 只有当队列空了，且没有被逻辑静音时，才发送真实音频
                    if getattr(self, '_ignore_audio_until', 0) > now:
                        await self._send_raw_audio(silent_chunk)
                    else:
                        # ... (发送真实音频的代码) ...
                        try:
                            audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                            audio_np = np.clip(audio_np * 8.0, -32768, 32767).astype(np.int16)
                            data_boosted = audio_np.tobytes()
                            
                            if int(now) % 3 == 0 and now % 1 < 0.1:
                                boosted_rms = np.sqrt(np.mean(audio_np.astype(np.float64)**2))
                                raw_rms = np.sqrt(np.mean(np.frombuffer(data, dtype=np.int16).astype(np.float64)**2))
                                print(f"[MIC INFO] Boosted RMS: {boosted_rms:.1f} (Raw: {raw_rms:.1f})")
                                
                            await self._send_raw_audio(data_boosted)
                        except Exception:
                            # Fallback to non-boosted audio if math fails
                            await self._send_raw_audio(data)
                else:
                    # 正在说话中，发送静音包压制麦克风
                    if self.is_active:
                         await self._send_raw_audio(silent_chunk)
                
            except websockets.exceptions.ConnectionClosed:
                print("\n⚠️ Send loop detected connection close.")
                raise 
            except Exception as e:
                print(f"Audio loop error: {e}")
                await asyncio.sleep(0.1)

    async def _send_raw_audio(self, data):
        """Helper to package and send audio according to Doubao protocol"""
        import jarvis_assistant.services.doubao.protocol as protocol
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
        from jarvis_assistant.utils.audio_utils import play_wake_sound, lower_music_volume
        
        # 1. Stop music IMMEDIATELY to free up audio device
        local_tool = self.tools.get("play_music")
        cloud_tool = self.tools.get("play_music_cloud")
        if local_tool: await local_tool.execute(action="stop")
        if cloud_tool: await cloud_tool.execute(action="stop")

        # 2. Duck volume for TTS/UI feedback
        lower_music_volume()
        
        # 3. Play wake sound
        # play_wake_sound()  <--- Decoupled: Managed by main loop now
        
        self.music_playing = False
        self.self_speaking_mute = False # Ensure mic is open
        self.bot_turn_active = False    # Ensure we can speak cleanly
        self.discard_incoming_audio = True # INTERRUPT: Ignore any trailing cloud audio
        print("🔊 Music stopped & Volume ducked - Jarvis is ready.")

    async def _monitor_music_processes(self):
        """Background loop to check if music players have finished naturally"""
        from jarvis_assistant.utils.audio_utils import restore_music_volume
        print("🔍 Music process monitor started.")
        while True:
            try:
                if self.music_playing:
                    # Check both local and cloud tools
                    local_player = self.tools.get("play_music")
                    cloud_player = self.tools.get("play_music_cloud")
                    
                    local_active = local_player and local_player._current_process and local_player._current_process.poll() is None
                    cloud_active = cloud_player and cloud_player._current_process and cloud_player._current_process.poll() is None
                    
                    if not local_active and not cloud_active:
                        # Music has finished naturally
                        print("\n🎵 Music finished naturally. Resuming mic...")
                        self.music_playing = False
                        self.self_speaking_mute = False
                        self.bot_turn_active = False
                        restore_music_volume()
                
                await asyncio.sleep(2.0) # Check every 2 seconds
            except Exception as e:
                print(f"⚠️ Monitor error: {e}")
                await asyncio.sleep(5.0)

    async def keyboard_input_loop(self):
        """Listen for keyboard input and send as text query"""
        import sys
        
        # --- BACKGROUND SAFETY ---
        allow_pipe = os.environ.get("JARVIS_ALLOW_STDIN_PIPE", "0") == "1"
        if not sys.stdin.isatty() and not allow_pipe:
            print("⌨️  Stdin is not a TTY. Keyboard monitoring disabled.")
            return

        if not sys.stdin.isatty() and allow_pipe:
            print("⌨️  Stdin pipe detected - processing input stream...")
            for line in sys.stdin:
                text = line.strip()
                if not text:
                    continue
                await self._handle_keyboard_text(text)
            return

        from asyncio import get_event_loop
        try:
            loop = get_event_loop()
            reader = asyncio.StreamReader()
            protocol_reader = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(lambda: protocol_reader, sys.stdin)
            
            print("⌨️  键盘监听已开启 - 直接输入文字即可...")
            
            while True:
                # Async read from stdin
                line = await reader.readline()
                if not line:
                    break
                    
                text = line.decode('utf-8').strip()
                if not text:
                    continue

                await self._handle_keyboard_text(text)
        except Exception as e:
            print(f"Keyboard loop not available: {e}")

    async def _handle_keyboard_text(self, text: str):
        # Special Handle: 'Jarvis' or '贾维斯' via keyboard acts as wake/stop
        sleep_keywords = ["退下", "休息", "闭嘴", "可以了", "再见", "拜拜", "退出", "休眠"]

        if text.lower() == "jarvis" or text == "贾维斯":
            print(f"\n⌨️ '{text}' typed! Waking up...")
            await self.stop_music_and_resume()
            self.is_active = True
            self.active_until = time.time() + self.ACTIVE_TIMEOUT
            # Lower volume for listening
            from jarvis_assistant.utils.audio_utils import lower_music_volume
            lower_music_volume()
            return

        if any(kw in text for kw in sleep_keywords):
            print(f"\n⌨️ '{text}' typed! Sleeping...")
            self.is_active = False
            self.active_until = 0
            # For keyboard, we need a manual confirm
            await self.send_text_query("System: 用户命令你休息。请仅用一个词（如“遵命”或“好”）礼貌回复。")
            # Restore volume for standby/music
            from jarvis_assistant.utils.audio_utils import restore_music_volume
            restore_music_volume()
            return

        print(f"📝 键盘输入: {text}")

        # If a response is active, optionally interrupt or wait (text-only)
        if self.text_only and self.pending_response:
            interrupt_keywords = ["打断", "停一下", "暂停", "取消", "停止", "别说了", "打住"]
            if self.bot_turn_active and any(k in text for k in interrupt_keywords):
                print("⚡ Interrupt: cancelling current response")
                try:
                    await self.send_reset_signal()
                except Exception as e:
                    print(f"⚠️ Interrupt reset failed: {e}")
                self.discard_incoming_audio = True
                self._mark_turn_done("interrupt")
            else:
                print("⏳ Waiting for current response to finish...")
                await self._wait_for_turn_slot(timeout=self.turn_timeout_seconds)

        # Typing any command also wakes Jarvis up
        self.is_active = True
        self.active_until = time.time() + self.ACTIVE_TIMEOUT

        # Check tools locally first (Optimization)
        try:
            if any(k in text for k in self.intent_keywords):
                await self.check_and_run_tool(text)
            else:
                # Send to Doubao for normal chat (will reply with voice)
                await self.send_text_query(text)
        except Exception as e:
            print(f"⚠️ Keyboard send failed: {e}")
            await asyncio.sleep(0.2)

    async def connect(self):
        import ssl
        import websockets
        import jarvis_assistant.services.doubao.protocol as protocol # Import Protocol
        
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
                print("✅ Connected!")
                
                # 1. StartConnection (Event 1)
                await self.send_start_connection()
                
                # 2. StartSession (Event 100)
                await self.send_start_session()
                
                # 3. Audio & Keyboard & Monitor
                self.text_send_queue = asyncio.Queue()
                if self.text_only:
                    if not self.local_tts_enabled:
                        self.setup_output_audio()
                    print("⌨️  Jarvis is alive. Type your message!")
                    await asyncio.gather(
                        self.receive_loop(),
                        self._text_sender_loop(),
                        self.keyboard_input_loop(),
                        self._monitor_music_processes()
                    )
                else:
                    self.setup_audio()
                    print("🎙️ Jarvis is alive. Speak or Type!")
                    await asyncio.gather(
                        self.receive_loop(),
                        self.send_audio_loop(),
                        self._text_sender_loop(),
                        self.keyboard_input_loop(),
                        self._monitor_music_processes()
                    )
                
        except Exception as e:
            print(f"❌ Error: {e}")

    async def send_start_connection(self):
        import jarvis_assistant.services.doubao.protocol as protocol
        
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

    async def send_start_session(self, wait_for_resp=True):
        import jarvis_assistant.services.doubao.protocol as protocol
        
        # Merge config with dynamic updates
        config_payload = start_session_req.copy()
        
        # Ensure we ask for standard PCM (Explicitly S16LE to avoid noise)
        config_payload["tts"]["audio_config"]["format"] = "pcm_s16le" 

        if self.text_only:
            config_payload.setdefault("dialog", {}).setdefault("extra", {})["input_mod"] = "text"
        
        print(f"⚙️ Session ID: {self.session_id} | Config: {json.dumps(config_payload, ensure_ascii=False)[:100]}...")
        
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
        if wait_for_resp:
            resp = await self.ws.recv()
            # Parse start session response to check for errors
            parsed = protocol.parse_response(resp)
            print(f"   StartSession Response: {parsed}")

    async def send_finish_session(self):
        """Send FinishSession (Event 102) to end current turn and refresh limit"""
        import jarvis_assistant.services.doubao.protocol as protocol
        if not self.ws: return
        
        print(f"🏁 Ending Session: {self.session_id}")
        req = bytearray(protocol.generate_header())
        req.extend((102).to_bytes(4, 'big'))
        
        session_bytes = self.session_id.encode('utf-8')
        req.extend(len(session_bytes).to_bytes(4, 'big'))
        req.extend(session_bytes)
        
        # Payload (Empty JSON)
        payload = gzip.compress(b"{}")
        req.extend(len(payload).to_bytes(4, 'big'))
        req.extend(payload)
        
        try:
            await self.ws.send(req)
        except Exception as e:
            print(f"⚠️ FinishSession failed: {e}")

    async def send_reset_signal(self, wait_for_resp: bool = True):
        """Perform a 'Hot Reset' (Finish old session, Rotate ID, Start new session)"""
        import uuid
        import asyncio
        if not self.ws: return

        # Avoid concurrent recv if receive_loop is active
        if self._receive_loop_task and not self._receive_loop_task.done():
            wait_for_resp = False
        
        try:
            # 1. End old session explicitly
            await self.send_finish_session()
            
            # CRITICAL: Wait for server to process FinishSession before starting new one
            # This prevents "session number limit exceeded" error
            await asyncio.sleep(0.3)
            
            # 2. Rotate Session ID
            old_id = self.session_id
            self.session_id = str(uuid.uuid4())
            print(f"🔄 Rotating Session ID: {old_id[:8]}... -> {self.session_id[:8]}...")
            
            # 3. Start new session (optionally wait for response)
            await self.send_start_session(wait_for_resp=wait_for_resp)
            print("✨ Cloud Hot Reset Complete")
            
        except Exception as e:
            print(f"⚠️ Cloud Reset Error: {e}")



    async def receive_loop(self):
        """Receive messages from Doubao and process them"""
        import jarvis_assistant.services.doubao.protocol as protocol
        import gzip
        import json
        
        # Track task for non-blocking gating
        self._receive_loop_task = asyncio.current_task()
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
                    if self.text_only:
                        continue
                    # Skip cloud audio if we're handling a local tool
                    if self.skip_cloud_response:
                        continue
                    if not self.processing_tool and isinstance(payload, bytes):
                        # --- INTERRUPT FIX: Handle discarded chunks ---
                        # Use a time-based window to kill trailing audio from last turn
                        if self.discard_incoming_audio or time.time() < getattr(self, 'ignore_server_audio_until', 0):
                            continue
                            
                        # ECHO FIX: Mute mic while we are pushing audio out
                        self.self_speaking_mute = True
                        self.last_audio_time = time.time()  # Track last audio chunk
                        
                        try:
                            # Non-blocking enqueue to speaker thread with drop-oldest strategy
                            try:
                                self.speaker_queue.put_nowait(payload)
                            except queue.Full:
                                # Buffer overflow - drop oldest packet to maintain real-time
                                try:
                                    self.speaker_queue.get_nowait()
                                    self.speaker_queue.put_nowait(payload)
                                    if time.time() % 5 < 0.1:
                                        print("⚠️ [AUDIO] Jitter buffer overflow - dropping oldest chunk")
                                except: pass
                        except Exception as e:
                            print(f"\n⚠️ Audio Enqueue Error: {e}")
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
                    
                    # --- INTERRUPT FIX: Stop discarding once we get a new event ---
                    self.discard_incoming_audio = False
                    
                    # --- VERBOSE LOGGING ---
                    if event.get('type') not in ['audio']:
                        print(f"\n📦 Event: {json.dumps(event, ensure_ascii=False)}")
                    
                    if not self.is_active:
                         # CLOUD WAKE: If we're in standby and receive any speech, wake up!
                         # This acts as a backup to the local Porcupine detector
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
                    
                    # Tool Activation & Wake Logic
                    if user_text:
                        print(f"\n🎧 User Speech: {user_text}")
                        
                        # WAKE LOGIC: If not active, check if user called 'Jarvis'
                        wake_keywords = ["jarvis", "贾维斯", "在吗", "你好", "hello", "hi"]
                        is_wake = any(kw in user_text.lower() for kw in wake_keywords)
                        
                        if not self.is_active and is_wake:
                            print("🌟 Cloud Wake: Activate session!")
                            self.is_active = True
                            self.active_until = time.time() + self.ACTIVE_TIMEOUT
                            # Also duck music immediately if needed
                            try:
                                from jarvis_assistant.utils.audio_utils import lower_music_volume
                                lower_music_volume()
                            except: pass
                        
                        # Only process tools and text if we are ACTIVE
                        if self.is_active:
                            self.active_until = time.time() + self.ACTIVE_TIMEOUT
                            await self.check_and_run_tool(user_text)
                    
                    if bot_text and self.is_active:
                        # Process protocols
                        await self.process_protocol_event(bot_text)

                        # CLEAN: Strip protocols and brackets from terminal display/TTS (if possible)
                        clean_text = re.sub(r'\[PROTOCOL:.*?\]', '', bot_text).strip()
                        
                        if clean_text:
                            if not self.bot_turn_active:
                                print(f"\n🗣️ Jarvis: ", end="", flush=True)
                                self.bot_turn_active = True
                            print(clean_text, end="", flush=True)
                            if self.local_tts_enabled:
                                self._bot_text_buffer.append(clean_text)
                                if self._tts_flush_task and not self._tts_flush_task.done():
                                    self._tts_flush_task.cancel()
                                self._tts_flush_task = asyncio.create_task(
                                    self._flush_tts_after_delay()
                                )
                        
                        # CRITICAL: Also reset timeout during speech to prevent mid-speech dropout
                        self.active_until = time.time() + self.ACTIVE_TIMEOUT
                    
                    # End of turn detection (Reset timeout and mic)
                    # Also check for 'finished' keyword in event type to catch more variations
                    event_type = event.get('type', '')
                    is_turn_end = (
                        'finished' in event_type
                        or 'done' in event_type
                        or event.get('done') == True
                        or event.get('no_content') == True
                    )

                    # DEBUG: Log event types to understand the protocol
                    if event_type and event_type not in ['audio', 'speech_segments', '']:
                        print(f"\n[DEBUG EVENT] type={event_type}", end="", flush=True)

                    # Error events should also release the turn gate
                    if event_type.lower() == 'error' or event.get('error'):
                        self._mark_turn_done("error")

                    if is_turn_end:
                        if self.bot_turn_active:
                            print("\n[Turn Finished]")
                            self.bot_turn_active = False
                            self.self_speaking_mute = False
                            self.active_until = time.time() + self.ACTIVE_TIMEOUT
                            print(f"⏱️ Jarvis finished. Listen window: 15s remaining.")
                        if self.local_tts_enabled and self._bot_text_buffer:
                            await self._flush_tts_buffer()
                        # Release turn gate
                        self._mark_turn_done("server_done")
                        
        except Exception as e:
             print(f"\n❌ Receive loop error: {e}")
             import traceback
             traceback.print_exc()

    def _mark_turn_done(self, reason: str = ""):
        """Mark current turn as done and release the gate."""
        if self.pending_response:
            self.pending_response = False
        if not self.turn_done.is_set():
            self.turn_done.set()
        if self.turn_timeout_task and not self.turn_timeout_task.done():
            self.turn_timeout_task.cancel()
        if reason:
            print(f"🟢 Turn released ({reason})")

    async def _wait_for_turn_slot(self, timeout: float = 25.0):
        if not self.turn_done.is_set():
            try:
                await asyncio.wait_for(self.turn_done.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                print("⚠️ Turn wait timeout. Forcing release.")
                self._mark_turn_done("timeout")

    async def _turn_timeout_guard(self):
        try:
            await asyncio.sleep(self.turn_timeout_seconds)
        except asyncio.CancelledError:
            return
        if self.pending_response:
            print("⚠️ Turn response timeout. Forcing release.")
            self._mark_turn_done("response_timeout")

    async def _enqueue_text_with_gate(self, text: str):
        await self._wait_for_turn_slot()
        self.pending_response = True
        self.turn_done.clear()
        if self.turn_timeout_task and not self.turn_timeout_task.done():
            self.turn_timeout_task.cancel()
        self.turn_timeout_task = asyncio.create_task(self._turn_timeout_guard())
        await self.text_send_queue.put(text)

    async def send_text_query(self, text: str):
        """Send text query to Doubao (triggers TTS response)"""
        print(f"📤 Sending text: {text}")

        if not self.text_send_queue:
            print("⚠️ text_send_queue not ready")
            return

        max_len = 1200
        if len(text) > max_len:
            text = text[:max_len] + "...(内容已截断)"

        # Avoid blocking receive_loop task; enqueue in background
        if asyncio.current_task() is self._receive_loop_task:
            asyncio.create_task(self._enqueue_text_with_gate(text))
            return

        await self._enqueue_text_with_gate(text)

    async def _flush_tts_after_delay(self, delay: float = 1.2):
        try:
            await asyncio.sleep(delay)
            await self._flush_tts_buffer()
        except asyncio.CancelledError:
            pass

    async def _flush_tts_buffer(self):
        text_to_speak = "".join(self._bot_text_buffer).strip()
        self._bot_text_buffer = []
        if text_to_speak:
            await self._speak_local(text_to_speak)

    async def _speak_local(self, text: str):
        import tempfile
        import subprocess
        import platform

        try:
            import edge_tts
        except Exception as e:
            print(f"⚠️ Local TTS unavailable: {e}")
            return

        voice = "zh-CN-YunxiNeural"
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
            output_path = fp.name

        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

            if platform.system() == "Darwin":
                subprocess.run(["afplay", output_path], check=False)
            else:
                subprocess.run(["mpv", "--no-video", output_path], check=False)
        finally:
            try:
                os.remove(output_path)
            except OSError:
                pass

    async def _text_sender_loop(self):
        import time
        while True:
            text = await self.text_send_queue.get()
            # Keep active mode alive while sending
            self.is_active = True
            self.active_until = time.time() + self.ACTIVE_TIMEOUT
            try:
                await self._send_text_payload(text)
            finally:
                self.text_send_queue.task_done()

    async def _send_text_payload(self, text: str):
        import jarvis_assistant.services.doubao.protocol as protocol
        payload = {"content": text}
        payload_bytes = gzip.compress(json.dumps(payload).encode('utf-8'))

        req = bytearray(protocol.generate_header(
            message_type=protocol.CLIENT_FULL_REQUEST,
            serial_method=protocol.JSON
        ))
        req.extend((501).to_bytes(4, 'big'))

        session_bytes = self.session_id.encode('utf-8')
        req.extend(len(session_bytes).to_bytes(4, 'big'))
        req.extend(session_bytes)

        req.extend(len(payload_bytes).to_bytes(4, 'big'))
        req.extend(payload_bytes)

        retries = 5
        for attempt in range(retries):
            try:
                await self.ws.send(bytes(req))
                return
            except OSError as e:
                if getattr(e, "errno", None) == 35 and attempt < retries - 1:
                    await asyncio.sleep(0.3)
                    continue
                raise
        


    async def process_protocol_event(self, bot_text: str):
        """Detect and execute Natural Language Triggers from bot text"""
        import re
        import random
        from jarvis_assistant.utils.audio_utils import restore_music_volume
        
        # Natural Language Triggers (Must match System Prompt exactly)
        TRIGGERS = {
            "光照系统已激活": "LIGHT_ON",
            "光照系统已关闭": "LIGHT_OFF",
            "正在接入音频流": "PLAY_MUSIC",
            "音频输出已切断": "MUSIC_STOP",
            "今日资讯简报如下": "GET_NEWS"
        }
        
        command = None
        for phrase, cmd in TRIGGERS.items():
            if phrase in bot_text:
                command = cmd
                print(f"\n🧠 Natural Intent Triggered: {phrase} -> {cmd}")
                break
        
        if not command:
            return

        try:
            if command == "LIGHT_ON":
                tool = self.tools.get("control_xiaomi_light")
                if tool: await tool.execute(action="on")
                
            elif command == "LIGHT_OFF":
                tool = self.tools.get("control_xiaomi_light")
                if tool: await tool.execute(action="off")
                
            elif command == "PLAY_MUSIC":
                tool = self.tools.get("play_music")
                all_music = tool._scan_music()
                if all_music:
                    import os
                    target = os.path.basename(random.choice(all_music))
                    print(f"🎲 Random play via Trigger: {target}")
                    await tool.execute(action="play", query=target)
                    self.music_playing = True
                    self.is_active = False
                    restore_music_volume()
            
            elif command == "MUSIC_STOP":
                await self.stop_music_and_resume()
                
            elif command == "GET_NEWS":
                from jarvis_assistant.services.tools import info_tools
                print("📰 Fetching news summary via Trigger...")
                result = await info_tools.get_news_briefing()
                # Feed result back to LLM to speak naturally
                prompt = f"System: 已获取今日头条。执行结果是：{result}。请用一个新闻主播的语气播报。"
                await self.send_text_query(prompt)

        except Exception as e:
            print(f"⚠️ Trigger execution failed: {e}")

    async def check_and_run_tool(self, text: str):
        """Check text for keywords and run tools"""
        import time
        import random
        from jarvis_assistant.core.intent_matcher import IntentMatcher
        
        # Extend active timeout on any interaction
        self.is_active = True
        self.active_until = time.time() + self.ACTIVE_TIMEOUT
        
        # Priority check for music stop/pause (Strict match only)
        # We only stop if the user explicitly says one of these as a standalone command 
        # or it's clearly a command to stop music.
        if text.strip() in ["停止", "暂停", "关掉", "闭嘴", "别播了", "切断", "停止播放"]:
            print(f"🛑 Local Explicit Stop Triggered: {text}")
            local_tool = self.tools.get("play_music")
            cloud_tool = self.tools.get("play_music_cloud")
            if local_tool: await local_tool.execute(action="stop")
            if cloud_tool: await cloud_tool.execute(action="stop")
            self.music_playing = False  
            self.self_speaking_mute = False 
            from jarvis_assistant.utils.audio_utils import restore_music_volume
            restore_music_volume()
            print("🎤 Mic resumed (music stopped manually)")
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
            
            from jarvis_assistant.utils.audio_utils import restore_music_volume
            restore_music_volume()
            return
        # NEW: Information Services (Regex based)
        # NEW: Information Services
        # 1. Stock/Crypto
        stock_query = IntentMatcher.match_stock(text)
        if stock_query:
            print(f"⚡ Detected Intent: get_stock_price ({stock_query})")
            self.processing_tool = True
            self.skip_cloud_response = True
            
            from jarvis_assistant.services.tools import info_tools
            result = await info_tools.get_stock_price(stock_query)
            
            # Send result
            prompt = f"System: 用户查询了股价。行情数据是：{result}。请用自然语言播报。"
            await self.send_text_query(prompt)
            
            self.processing_tool = False
            self.skip_cloud_response = False
            return

        # 2. News
        if IntentMatcher.match_news(text):
            print(f"⚡ Detected Intent: get_news")
            self.processing_tool = True
            self.skip_cloud_response = True
            
            from jarvis_assistant.services.tools import info_tools
            result = await info_tools.get_news_briefing()
            
            # Send result (News summary is already formatted for reading)
            # We can send it directly as "User says: Read this", or "System: Here is news"
            # Doubao might summarize it again. Let's just have Doubao read it.
            prompt = f"System: 用户想听新闻。这是抓取到的今日头条：\n{result}\n请用新闻主播的语气播报。"
            await self.send_text_query(prompt)
            
            self.processing_tool = False
            self.skip_cloud_response = False
            return

        for keyword, tool_name in self.intent_keywords.items():
            if keyword in text:
                print(f"\n⚡ Detected Intent: {tool_name}")
                self.processing_tool = True
                self.skip_cloud_response = True  # Mute Doubao's response
                self.discard_incoming_audio = True # IMMEDIATELY discard any concurrent server audio
                
                # Execute Tool
                tool = self.tools.get(tool_name)
                
                try:
                    # --- Intelligent Parameter Extraction ---
                    if tool_name == "get_weather":
                        city = IntentMatcher.match_weather(text)
                        print(f"📍 Extracted City: {city}")
                        result = await tool.execute(city=city)
 
                        
                    elif tool_name == "control_xiaomi_light":
                         action = IntentMatcher.match_light_control(text)
                         result = await tool.execute(ip="192.168.1.x", token="xxx", action=action)
                    
                    elif tool_name == "play_music":
                        action, query = IntentMatcher.match_music(text)
                        
                        if action == "stop":
                            result = await tool.execute(action="stop")
                        elif action == "list":
                            result = await tool.execute(action="list")
                        else:
                            # Play logic
                            if action == "play_random":
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
                                from jarvis_assistant.utils.audio_utils import restore_music_volume
                                restore_music_volume()
                                print("🔇 Mic muted (music playing) - Type '停止' to interrupt")

                    elif tool_name == "web_search":
                        query = IntentMatcher.match_web_search(text)
                        result = await tool.execute(query=query, num_results=3)
                        summary_lines = []
                        for line in result.splitlines():
                            line = line.strip()
                            if line.startswith("• "):
                                short = line[2:160]
                                summary_lines.append(short)
                        summary = "；".join(summary_lines[:3])
                        if summary:
                            result = f"搜索结果要点：{summary}"
                        
                    elif tool_name == "calculate":
                        # Extract math expression from text (supports 中文运算词)
                        expr = text
                        # Normalize common operators
                        expr = expr.replace("乘以", "*").replace("乘", "*")
                        expr = expr.replace("除以", "/").replace("除", "/")
                        expr = expr.replace("加", "+").replace("减", "-")
                        expr = expr.replace("×", "*").replace("÷", "/")
                        expr = expr.replace("＋", "+").replace("－", "-")
                        # Strip non-math characters
                        import re
                        expr = re.sub(r"[^0-9\.\+\-\*\/\(\)]", "", expr)
                        result = await tool.execute(expression=expr)
                        
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
                self.skip_cloud_response = False  # Resume listening to Doubao
                return

if __name__ == "__main__":
    # Ensure volume is high on boot
    from jarvis_assistant.utils.audio_utils import restore_music_volume, play_boot_sound
    restore_music_volume()
    
    # Play boot sequence once
    play_boot_sound()
    print("🚀 [STARTUP] Boot sound triggered, waiting 2s for audio device to stabilize...")
    time.sleep(2)
    
    print("🚀 [STARTUP] Initializing HybridJarvis instance...")
    jarvis = HybridJarvis()
    print("🚀 [STARTUP] HybridJarvis instance created")
    
    # Robust Reconnection Loop
    RETRY_DELAY = 1
    MAX_RETRIES = 5
    
    while True:
        try:
            print(f"\n🚀 Starting Jarvis (Auto-Reconnect Mode)...")
            print("🚀 Calling jarvis.connect()...")
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
