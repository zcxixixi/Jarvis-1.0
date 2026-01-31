#!/usr/bin/env python3
"""
Complete End-to-End Voice Pipeline Test
Text Input -> LLM Streaming -> TTS Streaming -> PyAudio Playback
"""
import asyncio
import time
import sys
import os
import pyaudio
import aiohttp
import json
import re

sys.path.append(os.getcwd())

from jarvis_assistant.services.doubao.tts_v3 import DoubaoTTSV1
from dotenv import load_dotenv

load_dotenv()

def clean_text_for_tts(text):
    """Remove emoji and validate text for TTS"""
    # Remove emoji and special unicode characters
    # Keep Chinese, English, numbers, and basic punctuation
    cleaned = re.sub(r'[^\u4e00-\u9fff\u3000-\u303fa-zA-Z0-9，。！？、；：""''（）《》\-\s,\.!\?;:\'\"\(\)]', '', text)
    
    # Remove extra whitespace
    cleaned = ' '.join(cleaned.split())
    
    # Check if there's any readable content left
    # (at least one Chinese character, letter, or number)
    if not re.search(r'[\u4e00-\u9fffa-zA-Z0-9]', cleaned):
        return None
    
    return cleaned

async def test_full_pipeline(user_input):
    print(f"\n{'='*60}")
    print(f"🧪 Complete Voice Pipeline Test")
    print(f"{'='*60}")
    print(f"📝 Input: {user_input}")
    print(f"{'='*60}\n")
    
    # Load API credentials
    api_key = os.getenv("DOUBAO_ARK_API_KEY")
    endpoint_id = os.getenv("DOUBAO_ENDPOINT_ID")
    
    # Setup TTS
    tts = DoubaoTTSV1()
    await tts.connect()
    
    # Setup PyAudio for playback
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=24000,
        output=True
    )
    
    # LLM Setup
    url = "https://ark.cn-beijing.volces.com/api/v3/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": endpoint_id,
        "input": [{
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": user_input}]
        }],
        "stream": True,
        "temperature": 0.7,
        "thinking": {"type": "disabled"}
    }
    
    if "lite" in endpoint_id or "251228" in endpoint_id:
        payload["reasoning"] = {"effort": "minimal"}
    
    print("🚀 Starting LLM generation...")
    start_time = time.time()
    llm_ttft = None
    audio_ttfb = None
    
    buffer = ""
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=15) as resp:
                if resp.status != 200:
                    print(f"❌ LLM Error: {await resp.text()}")
                    return
                
                print("🧠 LLM streaming started...")
                
                async for line in resp.content:
                    line_str = line.decode('utf-8').strip()
                    if not line_str or not line_str.startswith('data:'): 
                        continue
                    
                    data_str = line_str[5:].strip()
                    if data_str == '[DONE]': 
                        break
                    
                    try:
                        data = json.loads(data_str)
                        if data.get('type') == 'response.output_text.delta':
                            chunk = data.get('delta', '')
                            if chunk:
                                if llm_ttft is None:
                                    llm_ttft = (time.time() - start_time) * 1000
                                    print(f"⚡ LLM TTFT: {llm_ttft:.0f}ms")
                                
                                print(chunk, end="", flush=True)
                                buffer += chunk
                                
                                # Send to TTS on punctuation
                                if any(p in chunk for p in ["，", "。", "！", "？", ",", ".", "!", "?", "\n"]):
                                    text_to_speak = buffer.strip()
                                    buffer = ""
                                    
                                    # Clean text and skip if nothing readable
                                    cleaned_text = clean_text_for_tts(text_to_speak)
                                    if not cleaned_text:
                                        continue
                                    
                                    # Generate and play TTS
                                    async for audio_chunk in tts.synthesize(cleaned_text):
                                        if isinstance(audio_chunk, bytes):
                                            if audio_ttfb is None:
                                                audio_ttfb = (time.time() - start_time) * 1000
                                                print(f"\n🔊 Audio TTFB: {audio_ttfb:.0f}ms")
                                                print("🎵 Playing audio...\n")
                                            
                                            # Play audio directly
                                            stream.write(audio_chunk)
                    except Exception as e:
                        pass
        
        # Handle any remaining buffer
        if buffer.strip():
            cleaned_text = clean_text_for_tts(buffer.strip())
            if cleaned_text:
                async for audio_chunk in tts.synthesize(cleaned_text):
                    if isinstance(audio_chunk, bytes):
                        stream.write(audio_chunk)
                    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        stream.stop_stream()
        stream.close()
        p.terminate()
        await tts.close()
    
    total_time = (time.time() - start_time) * 1000
    
    print(f"\n\n{'='*60}")
    print(f"📊 Performance Summary:")
    print(f"  - LLM Response Start: {llm_ttft:.0f}ms")
    if audio_ttfb:
        print(f"  - First Sound Heard:  {audio_ttfb:.0f}ms")
        print(f"  - TTS Overhead:       {audio_ttfb - llm_ttft:.0f}ms")
    print(f"  - Total Time:         {total_time:.0f}ms")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = sys.argv[1]
    else:
        text = "你好，请简单介绍一下你自己。"
    
    asyncio.run(test_full_pipeline(text))
