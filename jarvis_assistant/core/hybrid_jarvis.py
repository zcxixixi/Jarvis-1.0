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
from datetime import datetime
import numpy as np
import queue
from typing import Optional
print("🚀 [TOP-LEVEL] Imports complete", flush=True)
from jarvis_assistant.services.doubao.websocket import DoubaoRealtimeJarvis
from jarvis_assistant.services.doubao.protocol import DoubaoMessage, MsgType, EventType, SerializationBits # Global imports
from jarvis_assistant.services.doubao.tts_bidirection import BidirectionalTTS
from jarvis_assistant.services.tools import get_all_tools
from jarvis_assistant.config.doubao_config import APP_ID, ACCESS_TOKEN, ws_connect_config, start_session_req, input_audio_config, output_audio_config, MICROPHONE_DEVICE_INDEX, INPUT_HARDWARE_SAMPLE_RATE, SPEAKER_DEVICE_INDEX
from jarvis_assistant.utils.audio_utils import play_boot_sound
from jarvis_assistant.services.audio.aec import get_aec
from jarvis_assistant.services.audio.asr_v2 import ASRServiceV2
import audioop # For high-quality resampling ratecv
from jarvis_assistant.services.doubao.tts_v3 import (
    synthesize_stream as tts_v3_synthesize,
    DoubaoTTSV1
)
from jarvis_assistant.utils.text_utils import clean_text_for_tts

class HybridJarvis(DoubaoRealtimeJarvis):
    async def on_text_received(self, text: str):
        """
        [Slow Brain Hook with Intelligent Routing]
        Called for both ASR and Keyboard text. 
        Routes to S2S (simple) or Agent (complex) based on query classification.
        """
        # 1. Echo/Shadow check
        if getattr(self, "_last_input_source", "") == "keyboard" and text.strip() == getattr(self, "_last_user_text", "").strip():
            self._last_input_source = "" 
            return

        # 2. [NEW] Intelligent Routing (Highest Priority after echo check)
        # This handles S2S vs Agent pathing and S2S suppression.
        await self.router.route(text)
    async def handle_trigger(self, prompt: str):
        """Callback for proactive triggers (e.g. reminders)"""
        print(f"⚡ Proactive Trigger in HybridJarvis: {prompt}")
        
        # 1. Transition to active mode so we can speak
        self._transition_to_active(reason="proactive_trigger")
        
        # 2. Get response from brain
        # Remove 'System Trigger: ' prefix if present for cleaner dialogue
        clean_prompt = prompt.replace("System Trigger: ", "")
        response = await self.brain.run(clean_prompt)
        
        # 3. Speak it!
        print(f"🗣️ Speaking Trigger Response: {response}")
        await self._send_tts_text(response)

    def __init__(self):
        print("🔧 HybridJarvis: Initializing...", flush=True)
        super().__init__()
        self.verbose_events = False # [DEBUG] Disable for production
        print("🔧 HybridJarvis: Base class initialized", flush=True)
        self.tools = {t.name: t for t in get_all_tools()}
        # Simplified intent mapping (in real app, use local LLM or fuzzy match)
        self.intent_keywords = {
            "天气": "get_weather",
            "几点": "get_current_time",
            "时间": "get_current_time",
            "计算": "calculate",
            "搜索": "web_search",
            "翻译": "translate",
            "翻一下": "translate",
            "翻译一下": "translate",
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
        # Buffer for printing bot text once (avoid per-token spam)
        self._bot_print_buffer = []
        self._bot_print_flush_task = None
        # Suppress cloud responses briefly after tool actions
        self.suppress_cloud_until = 0
        # Allow TTS audio even when suppressing cloud responses
        self.allow_tts_audio_until = 0
        # Tool TTS active window (mute mic to avoid echo)
        self.tool_tts_active_until = 0
        # Wake debounce
        self._ignore_wake_until = 0
        self._last_reset_time = 0

        # Turn-level gating to prevent out-of-order responses
        self.pending_response = False
        self.turn_done = asyncio.Event()
        self.turn_done.set()
        self.turn_timeout_task = None
        self.turn_timeout_seconds = 20
        self._receive_loop_task = None

        # Debug flags
        self.verbose_events = os.environ.get("JARVIS_VERBOSE", "0") == "1"
        self.verbose_mic = os.environ.get("JARVIS_VERBOSE_MIC", "0") == "1"
        self.force_allow_audio = False # [NEW] Robust override for Tool TTS

        # Last user/bot texts for logging
        self._last_user_text = ""
        self._last_bot_text = ""

        # Final response log path
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.project_root = root_dir
        self.final_log_path = os.environ.get(
            "JARVIS_FINAL_LOG",
            os.path.join(root_dir, "logs", "final_responses.jsonl")
        )
        # Realtime panel log (simple UI)
        self.panel_log_path = os.environ.get(
            "JARVIS_PANEL_LOG",
            os.path.join(root_dir, "logs", "realtime_panel.log")
        )

        # Optional capture of output audio for verification
        self.capture_tts = os.environ.get("JARVIS_CAPTURE_TTS", "0") == "1"
        self._tts_capture_active = False
        self._tts_capture_pending = False
        self._tts_capture_last_audio = 0
        self._tts_capture_user_text = ""
        self._tts_capture_expected = ""
        self._tts_capture_tool = ""
        self._tts_capture_source = ""
        self._tts_capture_id = ""
        self._tts_capture_seq = 0
        self._tts_capture_timeout_task = None
        self._tts_fallback_task = None
        self._tts_audio_buf = bytearray()
        self._tts_capture_path = None

        # Tool TTS modes: 500_fallback_local | 501_strict | local_only
        self.tool_tts_mode = os.environ.get("JARVIS_TOOL_TTS_MODE", "500_fallback_local").lower()
        self._tool_tts_strict_active = False
        self._tool_tts_expected = ""
        self._tool_tts_received = ""
        self._tool_tts_audio_buf = bytearray()
        self._tool_tts_audio_chunks = 0
        self._tool_tts_user_text = ""
        self._tool_tts_tool = ""
        self._tool_tts_timeout_task = None

        # [NEW] Initialize Cognitive Brain (Agent Core)
        from jarvis_assistant.core.agent import get_agent
        self.brain = get_agent()
        print("🧠 HybridJarvis: Cognitive Brain Connected (Singleton)")
        
        # Connect Scheduler to this instance for proactive speech
        from jarvis_assistant.core.scheduler import get_scheduler
        self.scheduler = get_scheduler()
        self.scheduler.set_callback(self.handle_trigger)
        print("⏰ HybridJarvis: Proactive Scheduler Linked")
        
        # [NEW] Start background monitoring for proactivity
        self._observer_task = None

        # [NEW] Bidirectional TTS for "Seamless" Dialogue
        self.bidir_tts = BidirectionalTTS()
        # Ensure TTS uses the configured voice
        from jarvis_assistant.config.doubao_config import start_session_req
        if "tts" in start_session_req and "speaker" in start_session_req["tts"]:
             # [FIX] Do NOT overwrite Bidir TTS speaker with S2S speaker
             # self.bidir_tts.voice_type = start_session_req["tts"]["speaker"]
             pass
        
        self._bidir_tts_player_task = None
        self._bidir_session_active = False
        
        # State machine: STANDBY (default) vs ACTIVE (after wake word)
        self.ACTIVE_TIMEOUT = 15  # 用户要求 15 秒自由沟通
        self.is_active = False # Standby by default
        self.active_until = 0
        # Optional: force always-active for debugging
        self.always_active = os.environ.get("JARVIS_ALWAYS_ACTIVE", "0") == "1"
        if self.always_active:
            self.is_active = True
            self.active_until = time.time() + 10**9
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
        
        # [NEW] Filler Phrase Manager for <1s latency masking
        from jarvis_assistant.services.audio.filler import FillerPhraseManager
        self.filler = FillerPhraseManager()
        
        # [NEW] Persistent TTS V1 for Transition Fillers & Deep Path
        # [OPTIMIZATION] Use singleton TTS (connection pooling)
        # Reduces latency by ~12% (reuses WebSocket connection)
        from jarvis_assistant.io.tts import get_doubao_tts
        self.tts_singleton = get_doubao_tts()
        
        # Legacy reference for compatibility (points to singleton's internal client)
        self.tts_v1 = self.tts_singleton.client
        
        print("🔌 HybridJarvis: TTS Singleton initialized (connection pooling enabled)")

        # [LATENCY FIX] Warm up connection proactively
        asyncio.create_task(self.tts_v1.connect())
        
        # [NEW] Query Router for intelligent S2S vs Agent routing
        from jarvis_assistant.core.query_router import QueryRouter
        # QueryRouter will use our pre-warmed brain/singleton
        self.router = QueryRouter(self)
        print("🔀 HybridJarvis: Query Router initialized")
        
        # [RESTORE] Resample states (Required for audio loop)
        self.mic_resample_state = None
        self.ref_resample_state = None

    def _safe_print(self, *args, **kwargs):
        try:
            msg = " ".join(map(str, args))
            print(*args, **kwargs)
            
            # [HOOK] Capture BOT output for UI panel logging
            if "🗣️" in msg and "Jarvis:" in msg:
                 clean_text = msg.split("Jarvis:")[-1].strip()
                 if hasattr(self, "_panel_log"):
                     self._panel_log(f"BOT: {clean_text}", "BOT")
                 
        except (BlockingIOError, OSError):
            # stdout backpressure; drop log to avoid crashing receive loop
            pass

    def _panel_log(self, message: str, level: str = "INFO"):
        try:
            if not message:
                return
            entry = {
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": level,
                "message": message,
            }
            os.makedirs(os.path.dirname(self.panel_log_path), exist_ok=True)
            with open(self.panel_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    async def _tts_capture_timeout(self, delay: float = 8.0):
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        if self._tts_capture_active or self._tts_capture_pending:
            self._finalize_tts_capture("timeout")

    def _prepare_tts_capture(self, user_text: str = "", expected_text: str = "", source: str = "", tool: str = "", timeout_seconds: float = 8.0):
        if not getattr(self, "capture_tts", False) or self.text_only:
            return
        # If an old capture is still around, finalize it to avoid leaks
        if self._tts_capture_active or self._tts_capture_pending:
            self._finalize_tts_capture("interrupted")
        self._tts_capture_seq += 1
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        capture_id = f"{ts}-{self._tts_capture_seq:02d}"
        self._tts_capture_id = capture_id
        self._tts_capture_path = os.path.join(self.project_root, "logs", f"tts_capture_{capture_id}.wav")
        self._tts_audio_buf = bytearray()
        self._tts_capture_pending = True
        self._tts_capture_active = False
        self._tts_capture_last_audio = 0
        self._tts_capture_user_text = user_text or ""
        self._tts_capture_expected = expected_text or ""
        self._tts_capture_tool = tool or ""
        self._tts_capture_source = source or ""
        if self._tts_capture_timeout_task and not self._tts_capture_timeout_task.done():
            self._tts_capture_timeout_task.cancel()
        if self._tts_fallback_task and not self._tts_fallback_task.done():
            self._tts_fallback_task.cancel()
        self._tts_capture_timeout_task = asyncio.create_task(self._tts_capture_timeout(timeout_seconds))

    def _finalize_tts_capture(self, reason: str = ""):
        if not getattr(self, "capture_tts", False):
            return
        if not (self._tts_capture_active or self._tts_capture_pending):
            return
        if self._tts_capture_timeout_task and not self._tts_capture_timeout_task.done():
            self._tts_capture_timeout_task.cancel()
        if self._tts_fallback_task and not self._tts_fallback_task.done():
            self._tts_fallback_task.cancel()
        # Write WAV (even if empty, for debugging)
        try:
            import wave
            os.makedirs(os.path.dirname(self._tts_capture_path), exist_ok=True)
            with wave.open(self._tts_capture_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(bytes(self._tts_audio_buf))
        except Exception:
            pass
        # Write meta mapping
        try:
            meta_path = os.path.join(self.project_root, "logs", "tts_capture_meta.jsonl")
            entry = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "capture_id": self._tts_capture_id,
                "audio_path": self._tts_capture_path,
                "user_text": self._tts_capture_user_text,
                "expected_text": self._tts_capture_expected,
                "source": self._tts_capture_source,
                "tool": self._tts_capture_tool,
                "reason": reason,
                "audio_bytes": len(self._tts_audio_buf),
                "session_id": self.session_id,
            }
            with open(meta_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # Reset flags
        self._tts_audio_buf = bytearray()
        self._tts_capture_active = False
        self._tts_capture_pending = False
        self._tts_capture_last_audio = 0
        self._tts_capture_user_text = ""
        self._tts_capture_expected = ""
        self._tts_capture_tool = ""
        self._tts_capture_source = ""
        self._tts_capture_id = ""
        self._tts_capture_path = None

    async def _tts_fallback_if_no_audio(self, text: str, capture_id: str, delay: float = 1.5):
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        if not capture_id or capture_id != self._tts_capture_id:
            return
        # If audio already arrived, do nothing
        if self._tts_capture_active or self._tts_audio_buf:
            return
        if not self._tts_capture_pending:
            return
        msg = "TTS audio not received; fallback to local TTS"
        self._safe_print(f"⚠️ {msg}")
        self._panel_log(msg, level="WARN")
        # Stop allowing late cloud audio
        self.allow_tts_audio_until = 0
        self.discard_incoming_audio = True
        self._finalize_tts_capture("fallback_no_audio")
        try:
            await self._speak_local(text)
        except Exception:
            pass

    def _schedule_tts_fallback(self, text: str, delay: float = 1.5):
        if not getattr(self, "capture_tts", False) or self.text_only:
            return
        if self._tts_fallback_task and not self._tts_fallback_task.done():
            self._tts_fallback_task.cancel()
        capture_id = self._tts_capture_id
        self._tts_fallback_task = asyncio.create_task(self._tts_fallback_if_no_audio(text, capture_id, delay))

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        try:
            return re.sub(r"\s+", "", text).strip()
        except Exception:
            return text.strip()

    async def _strict_tool_tts_timeout(self, delay: float = 3.0):
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        if self._tool_tts_strict_active:
            await self._strict_tool_tts_fallback("timeout")

    def _start_strict_tool_tts(self, expected: str, user_text: str, tool: str, timeout_seconds: float = 3.0):
        self._tool_tts_strict_active = True
        self._tool_tts_expected = expected or ""
        self._tool_tts_received = ""
        self._tool_tts_audio_buf = bytearray()
        self._tool_tts_audio_chunks = 0
        self._tool_tts_user_text = user_text or ""
        self._tool_tts_tool = tool or ""
        if self._tool_tts_timeout_task and not self._tool_tts_timeout_task.done():
            self._tool_tts_timeout_task.cancel()
        self._tool_tts_timeout_task = asyncio.create_task(self._strict_tool_tts_timeout(timeout_seconds))

    async def _strict_tool_tts_fallback(self, reason: str = "mismatch"):
        if not self._tool_tts_strict_active:
            return
        msg = f"Strict TTS mismatch ({reason}); fallback to local TTS"
        self._safe_print(f"⚠️ {msg}")
        self._panel_log(msg, level="WARN")
        # Discard buffered audio and ignore late cloud audio briefly
        self._tool_tts_audio_buf = bytearray()
        self._tool_tts_audio_chunks = 0
        self._tool_tts_strict_active = False
        self.ignore_server_audio_until = time.time() + 2.0
        self.discard_incoming_audio = True
        try:
            await self._speak_local(self._tool_tts_expected)
        except Exception:
            pass
        self._strict_tool_tts_reset()

    def _strict_tool_tts_reset(self):
        self._tool_tts_strict_active = False
        self._tool_tts_expected = ""
        self._tool_tts_received = ""
        self._tool_tts_audio_buf = bytearray()
        self._tool_tts_audio_chunks = 0
        self._tool_tts_user_text = ""
        self._tool_tts_tool = ""
        if self._tool_tts_timeout_task and not self._tool_tts_timeout_task.done():
            self._tool_tts_timeout_task.cancel()

    async def _strict_tool_tts_play_buffer(self):
        if not self._tool_tts_audio_buf:
            await self._strict_tool_tts_fallback("no_audio")
            return
        # Play buffered audio in chunks
        chunk_size = output_audio_config["chunk"] * 2  # 16-bit mono
        buf = bytes(self._tool_tts_audio_buf)
        for i in range(0, len(buf), chunk_size):
            try:
                self.speaker_queue.put_nowait(("agent", buf[i:i+chunk_size]))
            except queue.Full:
                try:
                    self.speaker_queue.get_nowait()
                    self.speaker_queue.put_nowait(("agent", buf[i:i+chunk_size]))
                except Exception:
                    pass
        self.last_audio_time = time.time()
        self.self_speaking_mute = True
        self._strict_tool_tts_reset()

    def _log_final_response(self, user_text: str = "", bot_text: str = "", source: str = "cloud", tool: str = "", expected: str = ""):
        try:
            if not bot_text:
                return
            # If we are capturing audio, fill expected text if missing
            if getattr(self, "capture_tts", False) and (self._tts_capture_active or self._tts_capture_pending):
                if not self._tts_capture_expected:
                    self._tts_capture_expected = bot_text
                if not self._tts_capture_user_text:
                    self._tts_capture_user_text = user_text or ""
                if not self._tts_capture_source:
                    self._tts_capture_source = source or ""
                if not self._tts_capture_tool:
                    self._tts_capture_tool = tool or ""

            entry = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "user_text": user_text,
                "bot_text": bot_text,
                "source": source,
                "tool": tool,
                "expected": expected,
                "session_id": self.session_id,
            }
            if getattr(self, "capture_tts", False) and self._tts_capture_path:
                entry["tts_capture"] = self._tts_capture_path
                entry["tts_capture_id"] = self._tts_capture_id
            os.makedirs(os.path.dirname(self.final_log_path), exist_ok=True)
            with open(self.final_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            # Also log to realtime panel (simple UI)
            self._panel_log(f"BOT: {bot_text}", level="BOT")
        except Exception:
            pass

    async def _speak_tool_result(self, result: str, tool: str, user_text: str):
        mode = self.tool_tts_mode
        # Mute mic during tool TTS to avoid echo/self-trigger
        self.self_speaking_mute = True
        tts_duration = max(6.0, min(20.0, len(result) * 0.12))
        self.tool_tts_active_until = time.time() + tts_duration

        if mode == "local_only":
            # Always local TTS (strict accuracy)
            self.skip_cloud_response = True
            self.suppress_cloud_until = time.time() + 4
            self.discard_incoming_audio = True
            try:
                self.last_audio_time = time.time()
                await self._speak_local(result)
            finally:
                if getattr(self, "capture_tts", False):
                    self._finalize_tts_capture("local_only")
            self._safe_print(f"🗣️ Jarvis: {result}")
            self._log_final_response(user_text=user_text, bot_text=result, source="tool", tool=tool, expected=result)
            asyncio.create_task(self._clear_skip_after_delay())
            asyncio.create_task(self._clear_tool_tts_after_delay(tts_duration))
            return

        if mode == "501_strict":
            # Use chat TTS but verify text strictly before playing audio
            self.skip_cloud_response = False
            self.suppress_cloud_until = 0
            self.discard_incoming_audio = False
            # Prepare capture and strict validation
            self._prepare_tts_capture(user_text=user_text, expected_text=result, source="tool", tool=tool, timeout_seconds=tts_duration + 2)
            self._start_strict_tool_tts(expected=result, user_text=user_text, tool=tool, timeout_seconds=3.5)
            strict_prompt = f"请严格逐字逐句复述以下内容，不要添加、删除、改写，仅输出原文：\n{result}"
            await self.send_text_query(strict_prompt)
            self._safe_print(f"🗣️ Jarvis: {result}")
            self._log_final_response(user_text=user_text, bot_text=result, source="tool", tool=tool, expected=result)
            # No skip-clear; handled on turn end
            asyncio.create_task(self._clear_tool_tts_after_delay(tts_duration))
            return

        # Default: 500 with local fallback
        self.skip_cloud_response = True
        self.suppress_cloud_until = time.time() + 6
        self.discard_incoming_audio = True

        # [NEW] Fusion: Use Bidirectional TTS (High Quality) for Tools if available
        if self.bidir_tts.is_connected and not self.text_only:
            try:
                if not self._bidir_session_active:
                    await self.bidir_tts.start_session()
                    self._bidir_session_active = True
                
                # Send text to Bidir TTS (streams audio to speaker_queue)
                await self.bidir_tts.send_text(result)
                
                self._safe_print(f"🗣️ Jarvis (Fusion): {result}")
                self._log_final_response(user_text=user_text, bot_text=result, source="tool_bidir", tool=tool, expected=result)
                
                # Manage state to prevent interruption
                asyncio.create_task(self._clear_skip_after_delay())
                # Allow longer window for streaming audio
                asyncio.create_task(self._clear_tool_tts_after_delay(tts_duration + 10.0))
                return
            except Exception as e:
                print(f"⚠️ Bidir TTS failed for tool: {e}. Falling back...")

        # Prepare capture (start on first audio chunk)
        self._prepare_tts_capture(user_text=user_text, expected_text=result, source="tool", tool=tool, timeout_seconds=tts_duration + 2)
        self.force_allow_audio = True # [NEW] Force allow audio for this duration
        try:
            # Prefer Doubao TTS-only for consistent voice
            await self._send_tts_text(result, allow_audio_seconds=tts_duration)
            # If no audio arrives quickly, fall back to local TTS
            self._schedule_tts_fallback(result, delay=1.5)
        except Exception:
            # Fallback to local TTS if TTS-only fails
            try:
                self.last_audio_time = time.time()
                await self._speak_local(result)
            finally:
                # Mark capture as ended (no cloud audio)
                if getattr(self, "capture_tts", False):
                    self._finalize_tts_capture("local_tts")
        self._safe_print(f"🗣️ Jarvis: {result}")
        self._log_final_response(user_text=user_text, bot_text=result, source="tool", tool=tool, expected=result)
        asyncio.create_task(self._clear_skip_after_delay())
        asyncio.create_task(self._clear_tool_tts_after_delay(tts_duration + 15.0))

    async def _speak_quick(self, text: str):
        """
        Quickly speak a short acknowledgment prompt using TTS 2.0.
        Non-blocking, fire-and-forget for UX improvement.
        """
        try:
            if self.bidir_tts.is_connected and not self.text_only:
                if not self._bidir_session_active:
                    await self.bidir_tts.start_session()
                    self._bidir_session_active = True
                await self.bidir_tts.send_text(text)
                print(f"🗣️ Quick: {text}")
        except Exception as e:
            print(f"⚠️ Quick speak failed: {e}")

    async def _clear_tool_tts_after_delay(self, delay: float = 6.0):
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        # finalize capture if still pending/active (backup)
        if getattr(self, 'capture_tts', False) and (self._tts_capture_active or self._tts_capture_pending):
            self._finalize_tts_capture("tool_timeout")
        self.tool_tts_active_until = 0
        self.self_speaking_mute = False
        self.discard_incoming_audio = False
        self.force_allow_audio = False # [NEW] Clear override

    def stop_speaking(self, reason: str = "interrupted"):
        """Immediately stop all current speech output"""
        if self.self_speaking_mute or self.bot_turn_active:
            print(f"[AUDIO] 🛑 Stopping speech | Reason: {reason}")
            
            # 1. Clear speaker queue
            if hasattr(self, 'speaker_queue'):
                while not self.speaker_queue.empty():
                    try:
                        self.speaker_queue.get_nowait()
                    except: break
                
            # 2. Reset flags
            self.self_speaking_mute = False
            self.bot_turn_active = False
            self.discard_incoming_audio = True
            self.ignore_server_audio_until = time.time() + 1.0
            
            # 3. Stop Bidirectional TTS if active
            if self.bidir_tts.is_connected and self._bidir_session_active:
                asyncio.create_task(self.bidir_tts.close()) # Or just finish_session
                self._bidir_session_active = False
                
            # 4. Signal turn done
            self._mark_turn_done(reason)

    def _transition_to_active(self, reason="unknown"):
        """Log state change to ACTIVE"""
        if not self.is_active:
            print(f"\n[STATE] 🟢 STANDBY -> ACTIVE | Reason: {reason}")
            self.is_active = True
            
        self.active_until = time.time() + self.ACTIVE_TIMEOUT
        
        # [NEW] Set source and suppression for Voice turns
        if reason == "wake_word":
            self._last_input_source = "voice"
            # [FIX] Default to ALLOWING cloud S2S. Only suppress if "Early Mute" or Router triggers.
            self.skip_cloud_response = False 
            # self.suppress_cloud_until = time.time() + 10.0 # Remove suppression default
            self._voice_asr_buffer = "" # Clear ASR buffer
        
        # [FIX] 唤醒后，如果音量处于 DUCK 状态，不要重复 DUCK
        from jarvis_assistant.utils.audio_utils import lower_music_volume, IS_DUCKED
        if not IS_DUCKED:
             lower_music_volume()

    def _transition_to_standby(self, reason="unknown"):
        """Log state change to STANDBY"""
        if self.is_active:
            # [LOGIC CHECK] 检查是否正在说话
            if self.self_speaking_mute or not self.speaker_queue.empty():
                print(f"[STATE] ⚠️ Warning: Transitioning to STANDBY while audio is still playing! (Reason: {reason})")
            
            print(f"\n[STATE] 🔴 ACTIVE -> STANDBY | Reason: {reason}")
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
        
        print(f"🎙️ Jarvis: Opening Mic (Default Device) at {INPUT_HARDWARE_SAMPLE_RATE}Hz...")
        
        # 尝试不同的通道数组合
        self.input_stream = None
        for ch in [1, 2]:
            try:
                self.input_stream = self.p.open(
                    format=input_audio_config["bit_size"],
                    channels=ch,
                    rate=INPUT_HARDWARE_SAMPLE_RATE,
                    input=True,
                    input_device_index=MICROPHONE_DEVICE_INDEX,
                    frames_per_buffer=input_audio_config["chunk"] * 3
                )
                print(f"✅ Jarvis: Mic opened successfully with {ch} channel(s).")
                break
            except Exception as e:
                print(f"⚠️ Mic failed with {ch} ch: {e}")
        
        if not self.input_stream:
            print("❌ Jarvis: All mic open attempts failed.")

        # [FIX] Mac 扬声器优化：采样率对齐 48000Hz，双声道，使用默认设备
        print(f"🎙️ Jarvis: Opening Speaker (Default Device) at 48000Hz (Stereo)...")
        try:
            self.output_stream = self.p.open(
                format=output_audio_config["bit_size"],
                channels=2, 
                rate=48000, 
                output=True,
                output_device_index=SPEAKER_DEVICE_INDEX
            )
            print("✅ Jarvis: Speaker opened successfully.")
        except Exception as e:
            print(f"❌ Jarvis: Failed to open speaker: {e}")
        
        import queue
        import threading
        self.speaker_queue = queue.Queue(maxsize=100) 
        self.speaker_thread = threading.Thread(target=self._speaker_worker, daemon=True)
        self.speaker_thread.start()
        
        # 初始化上采样状态
        self.output_upsample_state = None

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
                # [FIX] 检查输入流是否成功初始化
                if not hasattr(self, 'input_stream') or self.input_stream is None:
                    time.sleep(1.0)
                    continue

                data = self.input_stream.read(chunk_size, exception_on_overflow=False)
                if int(time.time()) % 5 == 0 and time.time() % 1 < 0.05:
                    print(f"🧵 [READER] Reading mic data... (len={len(data)})", flush=True)
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
                # Stop thread if event loop is closed (during reconnect)
                if "Event loop is closed" in str(e):
                    print("⚠️ Mic thread stopping: event loop closed")
                    break
                print(f"❌ Mic Thread Critical: {e}")
                time.sleep(0.1)


    def _speaker_worker(self):
        """
        [专用播放线程] 负责从队列获取 -> 转换 -> 写入声卡
        """
        import audioop
        print("🧵 [THREAD] Speaker Worker starting...")
        
        chunk_count = 0
        while self.is_running:
            try:
                # 阻塞等待音频数据
                data = self.speaker_queue.get(timeout=1.0)
                if data is None: continue 
                
                # [DEBUG] 打印前几个包的详细信息
                if chunk_count < 5:
                    # print(f"[AUDIO] 📦 Received chunk {chunk_count}")
                    pass

                # --- [SELECTIVE HARD GATE] ---
                # Unpack tag if present (tag, data)
                tag = "unknown"
                if isinstance(data, tuple):
                    tag, data = data
                
                # If it's S2S audio and we are suppressing Cloud (Agent Path active), DROP IT
                if tag == "s2s":
                    if getattr(self, "skip_cloud_response", False):
                         # print(f"🔇 [GATE] Dropped S2S packet (Size: {len(data)})")
                         self.speaker_queue.task_done()
                         continue
                    
                    # [SAFE-START BUFFER]
                    # If this is the START of a turn (chunk_count low), BUFFER IT briefly
                    # to give ASR time to detect keywords and flip the flag.
                    if chunk_count < 8: # Buffer first ~300ms
                         # Check if we have a buffer list
                         if not hasattr(self, "_s2s_safety_buffer"):
                             self._s2s_safety_buffer = []
                             self._s2s_safety_start_time = time.time()
                         
                         self._s2s_safety_buffer.append(data)
                         
                         # Check if we should release or keep holding
                         # Release if: Buffer full OR Time elapsed
                         if len(self._s2s_safety_buffer) >= 8 or (time.time() - self._s2s_safety_start_time > 0.4):
                             # Release all
                             # print(f"🔊 [BUFFER] Releasing {len(self._s2s_safety_buffer)} chunks")
                             for buffered_data in self._s2s_safety_buffer:
                                 # Re-check flag before playing each buffered chunk!
                                 if getattr(self, "skip_cloud_response", False):
                                     continue # Drop if flag flipped while buffering
                                 
                                 # PLAY LOGIC
                                 self._play_audio_data(buffered_data)
                                 
                             self._s2s_safety_buffer = [] # Clear
                         
                         self.speaker_queue.task_done()
                         continue
                
                # Normal Playback (Agent or S2S released)
                self._play_audio_data(data)
                self.speaker_queue.task_done()

            except queue.Empty:
                # Flush buffer on timeout/silence
                if hasattr(self, "_s2s_safety_buffer") and self._s2s_safety_buffer:
                     for buffered_data in self._s2s_safety_buffer:
                         if not getattr(self, "skip_cloud_response", False):
                             self._play_audio_data(buffered_data)
                     self._s2s_safety_buffer = []
                continue



    def _play_audio_data(self, data):
        """Helper to play raw audio data to hardware"""
        import audioop
        import time
        chunk_count = getattr(self, "_speaker_chunk_count", 0) + 1
        self._speaker_chunk_count = chunk_count
        
        # [AEC FIX] Mute mic while hardware is playing
        self.self_speaking_mute = True

        # --- [FIX] Mono-to-Stereo & Resampling ---
        try:
            # 1. 将单声道 (1ch) 转换为双声道 (2ch)
            # Realtime API 下发的通常是 16-bit PCM, 24000Hz, Mono
            stereo_data = audioop.tostereo(data, 2, 1, 1)
            
            # 2. 检查输出流采样率并重采样
            # 如果流是 48000Hz，我们需要 24000 -> 48000
            final_data, self.output_upsample_state = audioop.ratecv(
                stereo_data, 2, 2, 24000, 48000, self.output_upsample_state
            )
            
            # 3. 写入声卡
            self.output_stream.write(final_data, exception_on_underflow=False)
            
            if chunk_count % 10 == 0:
                print(f"[AUDIO] 🔊 Playing... (Chunk: {chunk_count})")

        except Exception as e:
            print(f"[AUDIO] ❌ Hardware playback error: {e}")

        # --- AEC Reference Feeding (Feed 16k mono for AEC) ---
        try:
            ref_chunk, self.ref_resample_state = audioop.ratecv(
                data, 2, 1, 24000, 16000, self.ref_resample_state
            )
            self.aec.feed_reference(ref_chunk)
        except: pass

        self.last_audio_time = time.time()

    async def send_audio_loop(self):
        """
        改进后的非阻塞音频循环：使用队列缓冲，彻底消除卡顿和丢帧。
        """
        import time
        import threading
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
                    if self.verbose_mic and rms > 10:
                        print(f"[MIC INFO] Level RMS: {rms:.1f}")

                # --- WAKE WORD GAIN BOOST (Increase to 10x for sensitivity) ---
                try:
                    wake_pcm = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
                    wake_pcm = np.clip(wake_pcm * 10.0, -32768, 32767).astype(np.int16)
                    data_for_wake = wake_pcm.tobytes()
                except:
                    data_for_wake = raw_data

                # 2. Local Wake Word Detection (feed 1280-sample chunks)
                # [FIX] Proceed to send logic even if active; skip wake word check if active or in ignore window
                if not self.is_active and now >= getattr(self, "_ignore_wake_until", 0) and time.time() >= getattr(self, 'tool_tts_active_until', 0):
                    if not hasattr(self, "_wake_buffer"):
                        self._wake_buffer = b""
                    self._wake_buffer += data_for_wake
                    
                    # Sensitivity control (lower is more sensitive)
                    try:
                        default_thr = float(os.environ.get("WAKE_THRESHOLD", "0.25"))
                    except Exception:
                        default_thr = 0.25
                    current_threshold = default_thr + (0.05 if self.music_playing else 0.0)

                    wake_triggered = False
                    while len(self._wake_buffer) >= 1280 * 2:
                        chunk = self._wake_buffer[:1280 * 2]
                        self._wake_buffer = self._wake_buffer[1280 * 2:]
                        if self.wake_detector and self.wake_detector.process_audio(chunk, threshold=current_threshold):
                            wake_triggered = True
                            if hasattr(self.wake_detector, 'reset'):
                                self.wake_detector.reset()
                            break

                    if wake_triggered:
                        # debounce wake triggers for a short window
                        self._ignore_wake_until = time.time() + 2.0
                        self._wake_buffer = b"" 
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
                        # Throttle hot reset to avoid loop on wake
                        if time.time() - getattr(self, '_last_reset_time', 0) > 2.5:
                            await self.send_reset_signal()
                            self._last_reset_time = time.time()
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
                else:
                    # Clear buffer to avoid backlog when active or ignored
                    if hasattr(self, "_wake_buffer"):
                        self._wake_buffer = b""

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
                is_speaking_now = (not self.speaker_queue.empty()) or self.self_speaking_mute or (time.time() < getattr(self, 'tool_tts_active_until', 0))
                
                # [DEBUG] 简化日志：活跃状态时每秒打印
                if self.is_active and int(now) != getattr(self, '_last_debug_sec', -1):
                    self._last_debug_sec = int(now)
                    # print(f"🎙️ [STATE] active={self.is_active}, speaking={is_speaking_now}, q_out={not self.speaker_queue.empty()}, mute={self.self_speaking_mute}", flush=True)
                
                
                if self.is_active and not is_speaking_now:
                    # 只有当队列空了，且没有被逻辑静音时，才发送真实音频
                    if getattr(self, '_ignore_audio_until', 0) > now:
                        # [FIX] Send silence during ignore period to keep connection alive but ignore input
                        await self._send_raw_audio(silent_chunk)
                    else:
                        # [MOD] S2S Audio Sending
                        # We send audio to S2S, which will trigger ASR and also cloud TTS (which we suppress)
                        try:
                            # Use config gain or default to 1.0
                            from jarvis_assistant.config.doubao_config import MIC_GAIN
                            gain = float(MIC_GAIN) if MIC_GAIN else 1.0
                            
                            audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                            audio_np = np.clip(audio_np * gain, -32768, 32767).astype(np.int16)
                            data_boosted = audio_np.tobytes()
                            
                            if self.verbose_mic and int(now) % 3 == 0 and now % 1 < 0.1:
                                boosted_rms = np.sqrt(np.mean(audio_np.astype(np.float64)**2))
                                raw_rms = np.sqrt(np.mean(np.frombuffer(data, dtype=np.int16).astype(np.float64)**2))
                                print(f"[MIC INFO] Gain: {gain}x | Boosted RMS: {boosted_rms:.1f} (Raw: {raw_rms:.1f})")
                                
                            await self._send_raw_audio(data_boosted)
                        except Exception as e:
                            # Fallback to non-boosted audio if math fails
                            # print(f"[AUDIO] Boost error: {e}")
                            await self._send_raw_audio(data)
                else:
                    # In standby or while speaking, send silence to keep session alive
                    await self._send_raw_audio(silent_chunk)
                
            except websockets.exceptions.ConnectionClosed:
                print("\n⚠️ Send loop detected connection close.")
                raise 
            except Exception as e:
                print(f"Audio loop error: {e}")
                await asyncio.sleep(0.1)

    async def _send_raw_audio(self, data):
        """Helper to package and send audio according to Doubao protocol"""
        
        # 使用重构后的消息对象进行构建，确保格式 100% 对齐官方 Demo
        msg = DoubaoMessage(
            type=MsgType.AudioOnlyClient,
            event=EventType.TaskRequest, # Event 200
            session_id=self.session_id,
            payload=data 
        )
        
        try:
            await self.ws.send(msg.marshal())
        except Exception as e:
            if self.verbose_mic: print(f"⚠️ Audio send failed: {e}")

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

        from asyncio import get_event_loop
        try:
            loop = get_event_loop()
            reader = asyncio.StreamReader()
            protocol_reader = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(lambda: protocol_reader, sys.stdin)
            
            if sys.stdin.isatty():
                print("⌨️  键盘监听已开启 - 直接输入文字即可...")
            else:
                print("⌨️  Stdin pipe detected - processing input stream...")
            
            while True:
                # Async read from stdin (TTY or pipe)
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
            # For keyboard, reply locally to avoid LLM confusion
            try:
                await self._send_tts_text("好")
            except Exception:
                pass
            # Restore volume for standby/music
            from jarvis_assistant.utils.audio_utils import restore_music_volume
            restore_music_volume()
            return

        print(f"📝 键盘输入: {text}")
        self._panel_log(f"USER: {text}", level="USER")
        self._last_user_text = text

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

        # Always run local tool check first
        try:
            handled = await self.check_and_run_tool(text)
            if handled is None:
                # If not handled by tool, send to Doubao for normal chat
                await self.send_text_query(text)
        except Exception as e:
            print(f"⚠️ Keyboard send failed: {e}")
            await asyncio.sleep(0.2)

    async def _bidir_tts_player_worker(self):
        """Background task to play audio from bidirectional TTS"""
        print("🔈 Bidirectional TTS Player Worker started.")
        while self.is_running:
            try:
                async for chunk in self.bidir_tts.audio_stream():
                    if chunk:
                        # Mute mic while speaking
                        self.self_speaking_mute = True
                        self.last_audio_time = time.time()
                        
                        try:
                            self.speaker_queue.put_nowait(("agent", chunk))
                        except queue.Full:
                            try:
                                self.speaker_queue.get_nowait()
                                self.speaker_queue.put_nowait(("agent", chunk))
                            except: pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Bidir TTS Player Error: {e}")
                await asyncio.sleep(0.5)

    async def _observer_loop(self):
        """Background loop that watches for noteworthy events to spark conversation"""
        print("🔍 Proactive Observer loop started.")
        last_weather_check = 0
        last_stock_check = 0
        last_news_check = 0
        last_activity_time = time.time()
        
        while self.is_running:
            try:
                now = time.time()
                
                # Check proactivity level from feedback
                level = self.brain.feedback.get_preferred_tool("proactivity_level") or "normal"
                if level == "low":
                     await asyncio.sleep(300) # Check less often
                     continue

                # Only spark if Jarvis is NOT already speaking and not active
                if not self.is_active and not self.self_speaking_mute:
                    
                    # 1. Weather Watcher (Every 1 hour, or on sudden change)
                    if now - last_weather_check > 3600:
                        last_weather_check = now
                        # We simulate a check. If it was real, we'd compare with previous.
                        # For the demo, let's just trigger a "Greeting" if it's afternoon
                        hour = datetime.now().hour
                        if 14 <= hour <= 17 and now - last_activity_time > 7200:
                             await self.handle_trigger("System Trigger: 看到先生一直在忙，主动打个招呼并播报一下当前菏泽天气情况")
                    
                    # 2. Stock Watcher (Every 30 mins during market hours)
                    if now - last_stock_check > 1800:
                        last_stock_check = now
                        # Check specific stocks like NVDA
                        # await self.handle_trigger("System Trigger: 检查一下英伟达股价是否有波动并汇报")
                        pass

                    # 3. Time-of-day contextual "Sparks"
                    if 15 <= hour <= 16 and now - last_news_check > 86400: # Once a day at 3pm
                         last_news_check = now
                         await self.handle_trigger("System Trigger: 主动播报一条今天最重要的科技新闻摘要")

                # If active, reset the idle timer
                if self.is_active:
                    last_activity_time = now
                
            except Exception as e:
                print(f"⚠️ Observer error: {e}")
            await asyncio.sleep(60)

    async def connect(self):
        import ssl
        import websockets
        import uuid
        import jarvis_assistant.services.doubao.protocol as protocol # Import Protocol
        
        # Use config from jarvis_doubao_config.py
        headers = ws_connect_config["headers"].copy()
        headers["X-Api-Connect-Id"] = str(uuid.uuid4())
        ws_url = ws_connect_config["base_url"]
        
        print(f"🤖 Connecting to Doubao...")
        
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        # Reset running flag for fresh connection
        self.is_running = True

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

                # [NEW] Connect Bidirectional TTS
                try:
                    await self.bidir_tts.connect()
                    self._bidir_tts_player_task = asyncio.create_task(self._bidir_tts_player_worker())
                except Exception as e:
                    print(f"⚠️ Failed to start Bidirectional TTS: {e}. Falling back to default.")
                
                # 3. Audio & Keyboard & Monitor
                self.text_send_queue = asyncio.Queue()
                if self.text_only:
                    if not self.local_tts_enabled:
                        self.setup_output_audio()
                    print("⌨️  Jarvis is alive. Type your message!")
                    # Start proactive observer
                    self._observer_task = asyncio.create_task(self._observer_loop())
                    
                    await asyncio.gather(
                        self.receive_loop(),
                        self._text_sender_loop(),
                        self.keyboard_input_loop(),
                        self._monitor_music_processes()
                    )
                else:
                    self.setup_audio()
                    print("🎙️ Jarvis is alive. Speak or Type!")
                    # Start proactive observer
                    self._observer_task = asyncio.create_task(self._observer_loop())
                    
                    await asyncio.gather(
                        self.receive_loop(),
                        self.send_audio_loop(),
                        self._text_sender_loop(),
                        self.keyboard_input_loop(),
                        self._monitor_music_processes()
                    )
                
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            # Ensure background threads exit cleanly on reconnect
            self.is_running = False
            try:
                if hasattr(self, "input_stream"):
                    self.input_stream.stop_stream()
                    self.input_stream.close()
            except Exception:
                pass
            try:
                if hasattr(self, "output_stream"):
                    self.output_stream.stop_stream()
                    self.output_stream.close()
            except Exception:
                pass
            self.ws = None

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
        
        # [CRITICAL] FORCE ASR CONFIG ENABLE
        # This overrides any potential missing config from file
        config_payload["asr"] = {
            "format": "pcm_s16le", 
            "language": "zh-CN",
            "need_check_punctuation": True,
            "need_text": True,
            "need_server_endpoint": True,
            "extra": {"end_smooth_window_ms": 800}
        } 

        if self.text_only:
            config_payload.setdefault("dialog", {}).setdefault("extra", {})["input_mod"] = "text"
        else:
             # Force 'audio' input mode if using mic, overriding any default 'text' config
             config_payload.setdefault("dialog", {}).setdefault("extra", {})["input_mod"] = "audio"
        
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
            
            # [FIX] 增加等待时间，确保服务端处理完旧会话释放资源，防止 55000001
            await asyncio.sleep(0.6)
            
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
        
        import websockets
        try:
            async for message in self.ws:
                if isinstance(message, str):
                    continue
                    
                # Use official protocol parser for robustness
                # It handles version, compression, and serialization
                result = protocol.parse_response(message)
                
                # [DEBUG] Trace incoming packets
                # print(f"[DEBUG] RX Packet: MsgType={result.get('message_type')} Event={result.get('event')}")
                if self.verbose_events and result.get('message_type') != '11':
                     print(f"[DEBUG] RX Packet: MsgType={result.get('message_type')} Event={result.get('event')}")
                
                # --- FIX: Immediate Turn Completion on Event 351 (TTSSentenceEnd) ---
                # This prevents the 15s timeout wait for the next turn
                evt_id = result.get('event')
                if evt_id in [351, 152, 102]: # 351=TTSSentenceEnd, 152=SessionFinished
                     # print(f"[TURN] 🏁 Server signaled turn end (Event {evt_id})")
                     if hasattr(self, '_mark_turn_done'):
                         self._mark_turn_done("server_done")
                
                if 'payload_msg' in result:
                     # Check if this is Audio (MsgType 11)
                     if result.get('message_type') == '11':
                         # [DEBUG] RX Audio
                         # print(f"[DEBUG] RX Audio: {len(result['payload_msg'])} bytes")
                         if hasattr(self, 'speaker_queue'):
                             try:
                                 # [ROUTER] Check if we should suppress S2S audio 
                                 if hasattr(self, 'router') and self.router.should_suppress_s2s():
                                     # print("🔇 [ROUTER] Skip S2S Audio chunk")
                                     continue

                                 self.self_speaking_mute = True
                                 self.last_audio_time = time.time()
                                 self.speaker_queue.put_nowait(("s2s", result['payload_msg']))
                             except Exception as e:
                                 print(f"[AUDIO] ❌ Queue push error: {e}")
                         continue

                     try:
                         # Try to parse payload as JSON for debug
                         pl = result['payload_msg']
                         if isinstance(pl, bytes):
                             pl = pl.decode('utf-8')
                         event_data = json.loads(pl)
                         # print(f"[DEBUG] RX Event Payload: {json.dumps(event_data, ensure_ascii=False)}")
                         # print(f"[DEBUG] RX Event: {event_data.get('type')}")
                     except Exception as e:
                         # pass # Not JSON
                         pass
                
                # Cleanup old unused logic
                # elif 'payload_audio' in result:
                #      pass

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
                    # [NEW] Skip ALL cloud audio if Bidirectional TTS is active
                    # This allows us to use BigTTS voices even if the Realtime API session isn't authorized for them
                    if self.bidir_tts.is_connected:
                        continue

                    # Skip cloud audio if we're handling a local tool (unless it's our TTS-only response)
                    if not self.force_allow_audio and (self.skip_cloud_response or time.time() < self.suppress_cloud_until) and time.time() >= self.allow_tts_audio_until:
                        continue
                    if isinstance(payload, bytes):
                        # --- INTERRUPT FIX: Handle discarded chunks ---
                        # Use a time-based window to kill trailing audio from last turn
                        if not self.force_allow_audio and (self.discard_incoming_audio or time.time() < getattr(self, 'ignore_server_audio_until', 0)) and time.time() >= self.allow_tts_audio_until:
                            continue
                            
                        # ECHO FIX: Mute mic while we are pushing audio out
                        self.self_speaking_mute = True
                        self.last_audio_time = time.time()  # Track last audio chunk

                        # TTS capture: start on first audio chunk, append as it streams
                        if getattr(self, "capture_tts", False):
                            if self._tts_capture_pending and not self._tts_capture_active:
                                self._tts_capture_active = True
                            if self._tts_capture_active:
                                self._tts_audio_buf.extend(payload)
                                self._tts_capture_last_audio = time.time()

                        # Strict tool TTS: buffer audio until text verified
                        if self._tool_tts_strict_active:
                            self._tool_tts_audio_buf.extend(payload)
                            self._tool_tts_audio_chunks += 1
                            # do not play yet
                        else:
                            try:
                                # Non-blocking enqueue to speaker thread with drop-oldest strategy
                                try:
                                    self.speaker_queue.put_nowait(("s2s", payload))
                                except queue.Full:
                                    # Buffer overflow - drop oldest packet to maintain real-time
                                    try:
                                        self.speaker_queue.get_nowait()
                                        self.speaker_queue.put_nowait(("s2s", payload))
                                        if time.time() % 5 < 0.1:
                                            print("⚠️ [AUDIO] Jitter buffer overflow - dropping oldest chunk")
                                    except: pass
                            except Exception as e:
                                print(f"\n⚠️ Audio Enqueue Error: {e}")
                                if "35" in str(e):
                                    pass
                                else:
                                    print(f"\n⚠️ Audio Playback Error: {e}")
                        
                        if self.verbose_events and time.time() % 5 < 0.1:
                             print(".", end="", flush=True)
                
                # --- FALLBACK: Unmute mic if no audio for 1 second ---
                if self.self_speaking_mute and self.last_audio_time > 0:
                    if time.time() - self.last_audio_time > 1.0:
                        print("\n[已恢复收音] Mic auto-resumed after speech pause")
                        # finalize capture on end-of-audio gap
                        if getattr(self, "capture_tts", False) and self._tts_capture_active:
                            self._finalize_tts_capture("silence")
                        self.self_speaking_mute = False
                        self.bot_turn_active = False
                        self.last_audio_time = 0
                        # Reset timeout for continuous conversation
                        self.active_until = time.time() + self.ACTIVE_TIMEOUT
                        
                        # [NEW] If a voice turn just ended and we have accumulated ASR, trigger it!
                        if getattr(self, "_last_input_source", "") == "voice" and getattr(self, "_voice_asr_buffer", ""):
                            final_text = self._voice_asr_buffer.strip()
                            self._voice_asr_buffer = "" # Clear for next
                            print(f"\n🎤 [VOICE TURN END] Processing accumulated ASR: {final_text}")
                            asyncio.create_task(self.on_text_received(final_text))
                
                
                # --- Case B: JSON Events ---
                elif serialization_type == protocol.JSON:
                    # [FIX] Ensure payload is parsed as JSON if it's currently bytes
                    event = payload
                    if isinstance(event, (bytes, bytearray)):
                        try:
                            event = json.loads(event.decode('utf-8'))
                        except Exception as e:
                            print(f"⚠️ Failed to parse JSON event: {e}")
                            continue
                            
                    if not isinstance(event, dict):
                        continue

                    # [DEBUG] BRUTE FORCE PRINT ALL EVENTS
                    # print(f"🔍 RAW EVENT: {str(event)[:300]}")
                    # If user starts speaking while Jarvis is speaking, stop Jarvis!
                    event_type = event.get('type', '')
                    is_user_speaking = (
                        'input_audio_transcription.started' in event_type
                        or 'input_audio_buffer.speech_started' in event_type
                        or event.get('type') == 'audio' # Some protocols send audio-only events as start cues
                    )
                    
                    if is_user_speaking and (self.bot_turn_active or self.self_speaking_mute):
                        self.stop_speaking(reason="barge_in")

                    # --- INTERRUPT FIX: Stop discarding once we get a new event ---
                    self.discard_incoming_audio = False
                    
                    # --- VERBOSE LOGGING ---
                    if self.verbose_events and event.get('type') not in ['audio']:
                        print(f"\n📦 Event: {json.dumps(event, ensure_ascii=False)}")
                    
                    if not self.is_active:
                         # CLOUD WAKE: If we're in standby and receive any speech, wake up!
                         # This acts as a backup to the local Porcupine detector
                         pass 

                    user_text = None
                    bot_text = None
                    
                    # 1. User ASR (Transcription)
                    # Support multiple event formats from different API versions
                    event_type = event.get('type', '')
                    if event_type == 'conversation.item.input_audio_transcription.completed':
                        user_text = event.get('transcript', '')
                    elif event_type == 'AudioInput':
                        # [CRITICAL] Accept 'active' state for PARTIAL results to enable Early Mute!
                        user_text = event.get('asr_text') or event.get('text')
                    elif event_type == 'ASR':
                        # Accept partials (is_final=False)
                        user_text = event.get('text')
                    elif 'asr_text' in event:
                        user_text = event.get('asr_text')
                    elif 'extra' in event and isinstance(event['extra'], dict):
                        # [FIX] Extract partial text (origin_text) IMPLICITLY for Early Mute
                        # We do NOT wait for 'endpoint' flag anymore
                        user_text = event['extra'].get('origin_text')
                    elif 'result' in event and isinstance(event['result'], dict):
                        # Catch-all for other ASR styles
                        user_text = event['result'].get('text')
                    
                    # 2. Bot Response (TTS Text)
                    if 'text' in event:
                        bot_text = event['text']
                    elif 'content' in event:
                        bot_text = event['content']
                    elif 'delta' in event: # [FIX] Support streaming delta
                        bot_text = event['delta']
                    
                    if bot_text:
                         print(f"\n[☁️ S2S TEXT] {bot_text}")
                    elif self.verbose_events:
                         print(f"[DEBUG] Event check keys: {list(event.keys())}")
                    
                    # Tool Activation & Wake Logic
                    if user_text:
                        # Ignore echoes 
                        if self.pending_response and user_text.strip() == self._last_user_text.strip():
                             continue
                             
                        # Ignore ASR results during tool TTS
                        if time.time() < getattr(self, 'tool_tts_active_until', 0):
                            continue
                        
                        self._last_user_text = user_text
                        
                        # Accumulate or process
                        # Accumulate or process
                        if getattr(self, "_last_input_source", "") == "voice":
                            # Stream ASR update with a clear indicator
                            if not hasattr(self, "_voice_asr_buffer"): self._voice_asr_buffer = ""
                            self._voice_asr_buffer = user_text 
                            # Use a persistent indicator for partial results
                            print(f"\n[👂 ASR PARTIAL] {user_text}")

                            # [NEW] Pre-emptive S2S Suppression (Early Mute)
                            # If we detect deep intent keywords in partial text, MUTE IMMEDIATELY
                            # asking price, searching, or tool keywords
                            mute_keywords = ["股价", "股票", "价格", "多少钱", "查一下", "搜索", "新闻", "天气", "计算", "翻译", "开灯", "关灯", "播放", "停止"]
                            if any(kw in user_text for kw in mute_keywords):
                                if not getattr(self, "skip_cloud_response", False):
                                    print(f"[🔒 PROACTIVE SUPERVISION] Intercepted S2S for keyword in: {user_text}")
                                    self.skip_cloud_response = True
                                    self.self_speaking_mute = True # Still mute mic for echo canx
                                    
                                    # [UX] Transition Fillers (Avoid silence gap)
                                    fillers = {
                                        "股价": "正在为您查询实时行情",
                                        "股票": "正在为您查询实时行情",
                                        "天气": "正在获取天气数据",
                                        "新闻": "正在同步最新资讯",
                                        "查询": "正在为您查询", # [FIX] Add generic query
                                        "查": "好的，正在为您查询", # [FIX] Add short query
                                        "播放": "好的，正在为您播放",
                                        "唱": "好的，来一首",
                                        "算": "正在计算",
                                        "翻译": "正在翻译"
                                    }
                                    filler = "好的，马上为您办理"
                                    for k, v in fillers.items():
                                        if k in user_text:
                                            filler = v
                                            break
                                            
                                    # Fire & forget Cloud TTS V3 for high-quality immediate feedback
                                    # [FIX] Use V3 (Standard TTS) to avoid Session Limit on Realtime API
                                    asyncio.create_task(self._speak_v3(filler))

                                    # Cear queue proactively
                                    if hasattr(self, 'speaker_queue'):
                                        while not self.speaker_queue.empty():
                                            try: self.speaker_queue.get_nowait()
                                            except: break
                            
                            # [NEW] Check for finality based on event type
                            is_final_event = (
                                event_type == 'conversation.item.input_audio_transcription.completed' 
                                or event_type == 'ASR' and event.get('is_final')
                                or 'finished' in event.get('state', '')
                            )
                            
                            if is_final_event:
                                print(f"\n🎤 [S2S FINAL] {user_text}")
                                self._panel_log(f"USER: {user_text}", level="USER")
                                
                                # Do NOT suppress S2S here! S2S is the default!
                                # Only suppress if Keyword matched (handled above) or Router says so.
                                # self.skip_cloud_response = True  <-- DELETE THIS
                                # self.suppress_cloud_until ...    <-- DELETE THIS 

                                await self.on_text_received(user_text)
                            
                            # [FALLBACK] If we see Bot Text but missed the "Final" signal, 
                            # force use the current buffer as final input.
                            elif bot_text and self._voice_asr_buffer:
                                print(f"\n🎤 [S2S FALLBACK] Response received, finalizing ASR: {self._voice_asr_buffer}")
                                user_text = self._voice_asr_buffer
                                # Treat as final
                                self._panel_log(f"USER: {user_text}", level="USER")
                                user_text = self._voice_asr_buffer
                                # Treat as final
                                self._panel_log(f"USER: {user_text}", level="USER")
                                # Do NOT mute S2S here. S2S is speaking (bot_text exists).
                                # self.skip_cloud_response = True  <-- DELETE
                                # self.filler.start ...            <-- DELETE
                                await self.on_text_received(user_text)
                        else:
                            # Direct trigger for text/system
                            print(f"\n🎧 User Speech (Keyboard/System): {user_text}")
                            self._panel_log(f"USER: {user_text}", level="USER")
                            
                            if self.is_active:
                                self.active_until = time.time() + self.ACTIVE_TIMEOUT
                                await self.on_text_received(user_text)
                    
                    if bot_text and self.is_active:
                        # [STRICT MUTE] If we are in voice mode, MUTE all bot text logging
                        # We only want the Brain's response which comes later via TTS
                        if getattr(self, "_last_input_source", "") == "voice":
                            continue 
                            
                        # Mute if suppressing cloud responses (for keyboard/brain)
                        if self.skip_cloud_response or time.time() < self.suppress_cloud_until:
                            continue
                        else:
                            # CLEAN: Strip protocols and brackets
                            clean_text = re.sub(r'\[PROTOCOL:.*?\]', '', bot_text).strip()
                            if clean_text:
                                print(f"\n🤖 Bot: {clean_text}")
                                self._panel_log(f"BOT: {clean_text}", level="BOT")

                            if self._tool_tts_strict_active:
                                if clean_text:
                                    self._tool_tts_received += clean_text
                                # Do not execute protocol actions while strict tool TTS is active
                                self.active_until = time.time() + self.ACTIVE_TIMEOUT
                            else:
                                # Process protocols
                                await self.process_protocol_event(bot_text)

                                if clean_text:
                                    # [NEW] Feed to Bidirectional TTS for "Seamless" output
                                    if self.bidir_tts.is_connected:
                                        if not self._bidir_session_active:
                                            await self.bidir_tts.start_session()
                                            self._bidir_session_active = True
                                        await self.bidir_tts.send_text(clean_text)

                                    # Buffer output to print only once
                                    self._bot_print_buffer.append(clean_text)
                                    self._last_bot_text += clean_text
                                    # schedule a delayed flush to print once after stream quiets
                                    if self._bot_print_flush_task and not self._bot_print_flush_task.done():
                                        self._bot_print_flush_task.cancel()
                                    self._bot_print_flush_task = asyncio.create_task(
                                        self._flush_bot_print_after_delay()
                                    )

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
                        # [NEW] End Bidirectional TTS Session
                        if self._bidir_session_active:
                            await self.bidir_tts.finish_session()
                            self._bidir_session_active = False

                        if self.bot_turn_active:
                            print("\n[Turn Finished]")
                            self.bot_turn_active = False
                            self.self_speaking_mute = False
                            self.active_until = time.time() + self.ACTIVE_TIMEOUT
                            print(f"⏱️ Jarvis finished. Listen window: 15s remaining.")

                        # Strict tool TTS validation
                        if self._tool_tts_strict_active:
                            expected = self._normalize_text(self._tool_tts_expected)
                            received = self._normalize_text(self._tool_tts_received)
                            if expected and received == expected:
                                await self._strict_tool_tts_play_buffer()
                            else:
                                await self._strict_tool_tts_fallback("mismatch" if received else "no_text")

                        # Flush buffered prints once
                        if self._bot_print_buffer:
                            await self._flush_bot_print_buffer()
                        if self.local_tts_enabled and self._bot_text_buffer:
                            await self._flush_tts_buffer()
                        # finalize capture at turn end
                        if getattr(self, "capture_tts", False) and (self._tts_capture_active or self._tts_capture_pending):
                            self._finalize_tts_capture("turn_end")
                        # Handle turn end
                        if event.get('event') in [protocol.EventType.SessionFinished, protocol.EventType.FinishSession, protocol.EventType.TTSSentenceEnd]:
                             print(f"[TURN] 🏁 Server signaled turn end (Event {event.get('event')})")
                             if hasattr(self, '_mark_turn_done'):
                                 self._mark_turn_done("server_done")
                        # Release turn gate
                        self._mark_turn_done("server_done")
                        # Clear cloud suppression after turn end
                        if time.time() >= self.suppress_cloud_until:
                            self.skip_cloud_response = False
                        
        except websockets.exceptions.ConnectionClosed:
             self._safe_print("\n⚠️ Receive loop connection closed.")
             raise
        except Exception as e:
             self._safe_print(f"\n❌ Receive loop error: {e}")
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
            print(f"[TURN] 🟢 Released | Reason: {reason}")

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
        self._last_input_source = "keyboard" # 标记来源
        self._last_user_text = text # 记录文本

        # [FIX] Check local tools first (Stock, News, Music) to avoid cloud hallucination
        # Requested by user validation failure "Apple stock price"
        if await self.check_and_run_tool(text):
            return

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

    async def _send_tts_text(self, content: str, allow_audio_seconds: float = 6.0):
        """Send text to S2S model with instruction to read it (Simulated TTS)"""
        # Since we only have the S2S connection, we trick the LLM into reading the text.
        # This is more reliable than trying to send TTS-protocol frames to an S2S endpoint.
        
        instruction = f"请准确朗读以下内容，不要做任何解释：{content}"
        
        # Reuse existing send_text_payload which handles the correct S2S protocol (Event 101/501 check)
        # Note: send_text_query checks for tools, so we use internal _send_text_payload 
        # or construct packet manually. Manual is safer to avoid loops.
        
        # Using correct S2S protocol for TextInput
        payload_data = {
            "type": "TextInput",
            "content": instruction
        }
        if hasattr(self, 'dialog_id') and self.dialog_id:
            payload_data["dialog_id"] = self.dialog_id

        msg = DoubaoMessage(
            type=MsgType.FullClientRequest,
            event=501, # Use valid TextInput event (confirmed in previous steps as 101 or 501, previous fix used 501/101 mismatch?)
                       # Wait, previous fix in receive_loop used 501. Let's check _send_text_payload
            session_id=self.session_id,
            payload=json.dumps(payload_data).encode('utf-8')
        )
        
        # Allow audio from this interaction
        self.allow_tts_audio_until = time.time() + allow_audio_seconds
        
        try:
             # Just use event 101 which we saw working in verify_robustness?
             # Actually EventType 101 is CancelSession? No.
             # Let's peek at _send_text_payload to be sure 
             await self._send_text_payload(instruction)
        except Exception as e:
            self._safe_print(f"⚠️ TTS Request failed: {e}")

    async def _flush_bot_print_after_delay(self, delay: float = 0.8):
        try:
            await asyncio.sleep(delay)
            await self._flush_bot_print_buffer()
        except asyncio.CancelledError:
            pass

    async def _flush_bot_print_buffer(self):
        text = "".join(self._bot_print_buffer).strip()
        self._bot_print_buffer = []
        if text:
            self._safe_print(f"\n🗣️ Jarvis: {text}")
            self._log_final_response(user_text=self._last_user_text, bot_text=text, source="cloud")
            self._last_bot_text = ""

    async def _clear_skip_after_delay(self, delay: float = 4.0):
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        self.skip_cloud_response = False

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

    def _play_pcm_bytes(self, pcm: bytes):
        import queue
        if not pcm:
            return
        chunk_size = output_audio_config["chunk"] * 2  # 16-bit mono
        for i in range(0, len(pcm), chunk_size):
            try:
                self.speaker_queue.put_nowait(("agent", pcm[i:i+chunk_size]))
            except queue.Full:
                try:
                    self.speaker_queue.get_nowait()
                    self.speaker_queue.put_nowait(("agent", pcm[i:i+chunk_size]))
                except Exception:
                    pass

    async def _speak_v3(self, text: str):
        """Use Doubao TTS V3 (Separate WebSocket) for fillers"""
        print(f"🔈 Cloud TTS V3: {text}")
        try:
             # Use the persistent instance
             async for chunk in self.tts_v1.synthesize(text):
                 self.speaker_queue.put_nowait(("agent", chunk))
        except Exception as e:
            print(f"⚠️ Cloud TTS V3 failed: {e}")
            pass

    async def _speak_stream(self, text_chunk: str, is_final: bool = False):
        """
        Streaming TTS handler: buffers text and sends to TTS on punctuation.
        [OPTIMIZED] with connection pooling.
        """
        if not hasattr(self, "_tts_stream_buffer"):
            self._tts_stream_buffer = ""
            
        self._tts_stream_buffer += text_chunk
        
        # Check for punctuation triggers or final signal
        buffer = self._tts_stream_buffer
        should_flush = is_final
        text_to_speak = ""
        
        # Punctuation triggers
        if any(p in text_chunk for p in ["，", "。", "！", "？", ",", ".", "!", "?", "\n", "：", ":"]):
             # Find the last punctuation index to split safely
             # For simplicity, if we hit a trigger, we try to speak everything
             should_flush = True
        
        if should_flush:
            text_to_speak = buffer.strip()
            self._tts_stream_buffer = "" # Reset buffer
            
            if text_to_speak:
                # Clean text
                cleaned = clean_text_for_tts(text_to_speak)
                if cleaned:
                    print(f"🔈 Stream TTS: {cleaned}")
                    try:
                        # [OPTIMIZATION] Ensure connection is reused (connection pooling)
                        await self.tts_singleton._ensure_connected()
                        
                        # Synthesize using singleton's client (reuses WebSocket)
                        async for chunk in self.tts_v1.synthesize(cleaned):
                            self.speaker_queue.put_nowait(("agent", chunk))
                    except Exception as e:
                        print(f"⚠️ Stream TTS failed: {e}")

    async def _speak_local(self, text: str):
    # [FIX] Re-enable local fallback as per user request to ensure audio output
    # print(f"DEBUG: Local fallback suppressed for: {text}")
        import asyncio
        print(f"🔈 Local TTS: {text}")
        try:
            # Use macOS 'say' command for high-quality local TTS
            proc = await asyncio.create_subprocess_exec(
                "say", "-r", "200", text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
        except Exception as e:
            print(f"⚠️ Local TTS failed: {e}")

    async def _text_sender_loop(self):
        import time
        import websockets
        while True:
            text = await self.text_send_queue.get()
            # Keep active mode alive while sending
            self.is_active = True
            self.active_until = time.time() + self.ACTIVE_TIMEOUT
            try:
                await self._send_text_payload(text)
            except websockets.exceptions.ConnectionClosed:
                self._safe_print("⚠️ WebSocket closed while sending text; reconnecting...")
                raise
            finally:
                self.text_send_queue.task_done()

    async def _send_text_payload(self, text: str):
        # [FIX] Align with websocket.py: Use Event 101 (TextInput)
        # payload_data = {"content": text}
        payload_data = {
            "type": "TextInput",
            "content": text
        }
        if hasattr(self, 'dialog_id') and self.dialog_id:
            payload_data["dialog_id"] = self.dialog_id
            
        msg = DoubaoMessage(
            type=MsgType.FullClientRequest,
            event=EventType.TextInput, # Use defined enum
            session_id=self.session_id,
            payload=json.dumps(payload_data).encode('utf-8')
        )

        import websockets
        from websockets.protocol import State
        retries = 5
        for attempt in range(retries):
            try:
                if not self.ws or getattr(self.ws, "state", None) != State.OPEN:
                    raise websockets.exceptions.ConnectionClosed(None, None)
                await self.ws.send(msg.marshal())
                return
            except websockets.exceptions.ConnectionClosed:
                raise
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
        
        print(f"[TOOL] 🔍 Analyzing intent for: '{text[:30]}...'")
        
        # Extend active timeout on any interaction
        self.is_active = True
        self.active_until = time.time() + self.ACTIVE_TIMEOUT
        
        # Priority check for music stop/pause (Strict match only)
        if text.strip() in ["停止", "暂停", "关掉", "闭嘴", "别播了", "切断", "停止播放"]:
            print(f"[TOOL] 🛑 Manual stop override triggered.")
            local_tool = self.tools.get("play_music")
            cloud_tool = self.tools.get("play_music_cloud")
            if local_tool: await local_tool.execute(action="stop")
            if cloud_tool: await cloud_tool.execute(action="stop")
            self.music_playing = False  
            self.self_speaking_mute = False 
            from jarvis_assistant.utils.audio_utils import restore_music_volume
            restore_music_volume()
            return True

        # Priority check for Sleep/Standby
        sleep_keywords = ["退下", "休息", "可以了", "再见", "拜拜", "退出", "休眠"]
        if any(kw in text for kw in sleep_keywords):
            if not self.is_active: return # Already standby
            print(f"[TOOL] 💤 Sleep intent detected: {text}")
            self.is_active = False
            self.active_until = 0
            from jarvis_assistant.utils.audio_utils import restore_music_volume
            restore_music_volume()
            return True

        # 🔥 UNIFIED ARCHITECTURE (Phase 7):
        # All other intents (Stock, News, Weather, Music Search, Translation)
        # are now strictly routed to JarvisAgent via QueryRouter.
        # This method ONLY handles critical system interrupts for safety.
        
        return None

        # Priority check for Sleep/Standby
        sleep_keywords = ["退下", "休息", "可以了", "再见", "拜拜", "退出", "休眠"]
        if any(kw in text for kw in sleep_keywords):
            if not self.is_active: return # Already standby
            print(f"[TOOL] 💤 Sleep intent detected: {text}")
            self.is_active = False
            self.active_until = 0
            from jarvis_assistant.utils.audio_utils import restore_music_volume
            restore_music_volume()
            return True

        # NEW: Information Services (Regex based) - MOVED TO AGENT
        # stock_query = IntentMatcher.match_stock(text)
        # Unified Architecture: Agent handles stocks.

        # News logic moved to Agent.

        for keyword, tool_name in self.intent_keywords.items():
            if keyword in text:
                print(f"[TOOL] 🎯 Key match: '{keyword}' -> {tool_name}")
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
                        
                        # Say "querying" prompt first for better UX
                        import random
                        loading_prompts = ["好的，正在为您查询", "稍等，马上为您查看", "让我看看", "好的，查一下"]
                        prompt = random.choice(loading_prompts) + f"{city}的天气"
                        asyncio.create_task(self._speak_quick(prompt))
                        
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

                    elif tool_name == "translate":
                        # Simple translation intent
                        to_lang = None
                        if any(k in text for k in ["英文", "英语", "english", "EN"]):
                            to_lang = "en"
                        if any(k in text for k in ["中文", "汉语", "Chinese", "ZH"]):
                            to_lang = "zh"
                        # Remove trigger words
                        q = text
                        for w in ["翻译", "翻一下", "翻译一下", "翻成", "翻译成", "帮我", "一下", "请"]:
                            q = q.replace(w, "")
                        q = q.strip()
                        if to_lang:
                            result = await tool.execute(text=q, to_lang=to_lang)
                        else:
                            result = await tool.execute(text=q)
                        
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
                
                # Speak result directly (no LLM) to avoid double/incorrect responses
                if tool_name in ["play_music", "play_music_cloud"]:
                    self.processing_tool = False
                    return True 

                self.skip_cloud_response = True
                self.suppress_cloud_until = time.time() + 4
                await self._speak_tool_result(result, tool_name, text)
                
                self.processing_tool = False
                return True

        return None

    def _clear_speaker_queue(self):
        """Purge any pending audio chunks (e.g. S2S) from the queue"""
        dropped = 0
        while not self.speaker_queue.empty():
            try:
                self.speaker_queue.get_nowait()
                self.speaker_queue.task_done()
                dropped += 1
            except queue.Empty:
                break
        if dropped > 0:
            print(f"🔇 [AUDIO] Purged {dropped} chunks from speaker queue.")

    def _mark_turn_done(self, reason: str = "unknown"):
        """Called when server turn ends (e.g. event 351/152/102)"""
        if getattr(self, "verbose_events", False):
            print(f"[TURN] 🟢 Released | Reason: {reason}")
        
        # [CRITICAL] Handoff to Agent if S2S was suppressed
        if getattr(self, "skip_cloud_response", False):
            if hasattr(self, "_voice_asr_buffer") and self._voice_asr_buffer:
                buffer_text = self._voice_asr_buffer.strip()
                print(f"[HANDOFF] 🔄 Turn done with S2S suppressed. Triggering Agent with: {buffer_text}")
                
                # [FIX] Force clear any S2S audio that might have snuck in before suppression
                self._clear_speaker_queue()
                
                # [FIX] Extend active timeout to give Agent time to process (30 seconds)
                self.active_until = time.time() + 30
                
                # [FIX] Do NOT reset skip_cloud_response here!
                # The router._handle_agent_path will reset it when done.
                # self.skip_cloud_response = False  # <-- REMOVED - causes race condition
                
                # Execute Agent Logic
                asyncio.create_task(self.on_text_received(buffer_text))
            else:
                 print("[HANDOFF] ⚠️ S2S suppressed but no text buffer found!")
        else:
             # Normal S2S turn ended
             pass
             
        # Reset state
        self.discard_incoming_audio = False
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
8