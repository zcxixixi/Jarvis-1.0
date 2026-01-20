
import asyncio
import os
import io
import pyaudio
from cartesia import Cartesia
from rich.console import Console

# 导入配置
from config import Config
from jarvis_core import JarvisCore

console = Console()

# Cartesia Configurations
CARTESIA_API_KEY = "sk_car_f5k7zJEV3AiNorLHgio9M9"
# Voice ID: A deep male voice (British/Jarvis-like if available, otherwise a good default)
# "a0e99841-438c-4a64-b679-ae501e7d6091" is "Barbershop Man" - Deep & Resonant
# Let's use a known high quality male voice ID for demo. 
# You can change this ID later from Cartesia library.
VOICE_ID = "a0e99841-438c-4a64-b679-ae501e7d6091" 
MODEL_ID = "sonic-english" # Or sonic-multilingual for Chinese support?
# Cartesia "Sonic Multilingual" supports Chinese!
MODEL_ID = "sonic-multilingual" 

class JarvisCartesia:
    def __init__(self):
        self.console = Console()
        self.core = JarvisCore()
        
        # Audio Setup
        self.p = pyaudio.PyAudio()
        self.rate = 44100 
        
        # Init Cartesia Client
        self.client = Cartesia(api_key=CARTESIA_API_KEY)
        self.voice_id = VOICE_ID
        self.console.print("✅ Cartesia Client Ready", style="green")

    def get_input(self):
        """Get text input from user"""
        try:
            text = self.console.input("[bold green]You: [/]")
            return text
        except (EOFError, KeyboardInterrupt):
            return None

    def stream_audio(self, text_stream):
        """
        Takes a text generator (LLM stream) and pipes it to Cartesia TTS Stream.
        Everything runs in real-time.
        """
        # Open Audio Stream
        stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            output=True
        )

        # Create Cartesia WebSocket Context
        ws = self.client.tts.websocket()
        context = ws.context(
            model_id=MODEL_ID,
            voice_id=VOICE_ID,
            output_format={
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": 44100,
            },
        )

        try:
            # We buffer text slightly to avoid sending single characters which might sound glitchy
            buffer = ""
            
            for chunk in text_stream:
                print(chunk, end="", flush=True) # Print LLM text
                
                # Send to TTS
                # Cartesia is very fast, we can just send chunks.
                # But grouping by sentence or phrase is usually safer for intonation.
                # For ultra-low latency, we just send.
                context.send(chunk) 

                # Read audio from WS and play immediately
                # Note: Cartesia SDK manages the receiving in background or via iterator?
                # Actually, standard usage is: context.send(text), then iterate context.receive()
                
                # Wait, we need to interleave sending and receiving? 
                # Or run receiving in a separate thread/task.
                
                # Simplified approach: Send everything, then receive everything? 
                # No, that defeats "streaming LLM".
                
                # Let's capture chunks and send them.
                # But to play audio WHILE generating text, we need async or threading if using this sync loop.
                # However, this method `stream_audio` is designed to consume the text stream.
                
                # Let's act as a generator that yields audio?
                pass
            
            context.no_more_inputs() # Tell logic we are done sending text

            # Receive and Play loop
            # Note: If we do send -> send -> send -> no_more -> receive loop, 
            # we only hear audio after LLM connects? 
            # Ideally we want full duplex.
            
            # The Cartesia Python SDK `websocket()` context is an iterator of events!
            # But we need to feed it inputs via `context.send()`.
            
        except Exception as e:
            self.console.print(f"\nTTS Error: {e}", style="red")
        finally:
            stream.stop_stream()
            stream.close()
            ws.close()

    def _clean_text(self, text):
        """Remove markdown and symbols for better TTS"""
        import re
        # Remove markdown bold/italic
        text = text.replace("*", "").replace("#", "").replace("- ", "")
        return text

    def run_sync_simple(self):
        """
        Voice Interaction Loop
        """
        self.console.print("🤖 Jarvis (Cartesia Sonic Mode)", style="bold purple")
        
        # Inject Voice-Optimized System Prompt (Appended to existing history or prepended)
        # We want Jarvis to be conversational, not use lists.
        voice_instruction = {
            "role": "system", 
            "content": (
                "You are Jarvis, a helpful AI assistant. "
                "Current Mode: Voice Conversation (Text-to-Speech active). "
                "IMPORTANT: "
                "1. Keep answers CONCISE and short (1-2 sentences). "
                "2. Do NOT use markdown formatting (no * lists, no # headers). "
                "3. Speak naturally as if talking, not reading a document. "
                "4. Do NOT apologize for being an AI. Just help directly. "
                "5. Start with 'Yes, sir' or 'Right away' occasionally."
                f"Current Time: 2026-01-18" # Hardcoded for now to fix 'I don't know time'
            )
        }
        # Clear/Reset history with this new prompt
        self.core.history = [voice_instruction]

        # Open Audio Output (Global)
        self.audio_stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=44100,
            output=True
        )
        
        while True:
            try:
                user_text = self.get_input()
                if not user_text or user_text.lower() in ['exit', 'quit']:
                    break
                
                print("Jarvis: ", end="", flush=True)
                
                # Setup Cartesia SSE Stream
                # This is much simpler than WebSocket and still low latency
                
                # We need a generator that yields text chunks, but SSE client usually wants full text or an iterator?
                # Cartesia SSE client `tts.sse` takes a `transcript` which can be a string or iterator.
                # Let's see if we can pass a generator. If not, we fall back to accumulating.
                
                # Check SDK capability: usually `sse(..., transcript=iterator)` works for streaming input too?
                # If not, let's just accumulate sentence by sentence for stability, or just full text.
                # But user wants low latency.
                
                # Let's try to stream LLM into it?
                # Most Python SDKs for TTS take a string. 
                # Let's try to pass the generator.
                
                # Actually, to be safe and ensure it works NOW:
                # 1. We accumulate text from LLM in background.
                # 2. But we want audio ASAP.
                
                # Let's try sending chunks to `sse`? No, that would make multiple requests.
                # WebSocket is for that. SSE is usually request-response stream.
                
                # Compromise: We accumulate specific punctuation (sentence) then send to TTS.
                # This is "Sentence Buffer" mode.
                
                # Buffer logic
                buffer = ""
                print(f"\n[Debug] Starting LLM stream...")
                
                llm_stream = self.core.chat_stream(user_text)
                
                for chunk in llm_stream:
                    print(chunk, end="", flush=True)
                    buffer += chunk
                    
                    # Smart Buffering:
                    # Only send if we hit a strong punctuation AND buffer is long enough (e.g. > 30 chars)
                    # This reduces "choppy" sentences.
                    is_terminator = any(p in chunk for p in [".", "!", "?", "。", "！", "？", "\n"])
                    
                    if is_terminator:
                        # If buffer is long enough, send it. 
                        # Or if it's a very strong pause like newline.
                        if len(buffer) > 30 or "\n" in chunk:
                            if buffer.strip():
                                print(f"\n[Debug] ⚡️ Sending accumulated buffer ({len(buffer)} chars)...")
                                self.play_sentence(buffer)
                                buffer = ""
                        else:
                             # Keep buffering small sentences to merge them for better prosody
                             pass
                
                # Flush remaining
                if buffer.strip():
                    print(f"\n[Debug] ⚡️ Flush sending: '{buffer.strip()}'")
                    self.play_sentence(buffer)
                    
                print() # Newline
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.console.print(f"\n[Main Loop Error]: {e}", style="red")

    def play_sentence(self, text):
        """Helper to play a single sentence via Cartesia SSE"""
        try:
            # Clean text (remove Markdown)
            text = self._clean_text(text)
            if not text.strip(): return

            print(f"[Debug] Calling client.tts.sse for: {text[:10]}...")
            
            output = self.client.tts.sse(
                model_id=MODEL_ID,
                voice={
                    "mode": "id",
                    "id": self.voice_id
                },
                transcript=text,
                output_format={
                    "container": "raw",
                    "encoding": "pcm_f32le",
                    "sample_rate": 44100,
                },
                language="zh"
            )
            
            print(f"[Debug] Response stream iterator started...")
            chunk_count = 0
            for chunk in output:
                payload = None
                
                # Broad attribute check
                if hasattr(chunk, "data"):
                    payload = chunk.data
                elif hasattr(chunk, "audio"):
                    payload = chunk.audio
                elif isinstance(chunk, dict):
                    payload = chunk.get("data") or chunk.get("audio")
                else:
                    payload = chunk # Maybe raw bytes

                if payload:
                    # Decoding check
                    if isinstance(payload, str):
                        try:
                            import base64
                            payload = base64.b64decode(payload)
                        except:
                            pass # Not base64
                            
                    if isinstance(payload, bytes):
                        self.audio_stream.write(payload)
                        chunk_count += 1
                        if chunk_count % 10 == 0:
                            print(".", end="", flush=True)

            print(f" [Audio Played: {chunk_count} chunks]")
                    
        except Exception as e:
            print(f"\n[TTS API Error]: {e}")
            
        # Do NOT close stream here, keep it open for next sentence chunk

if __name__ == "__main__":
    jarvis = JarvisCartesia()
    jarvis.run_sync_simple()
