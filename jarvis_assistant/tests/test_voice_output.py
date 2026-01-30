#!/usr/bin/env python3
"""
Test Jarvis TTS Output
Sends a prompt to Doubao (ARK) if available, otherwise uses a fixed response,
then plays through speaker using edge-tts
"""
import asyncio
import subprocess
import os
import sys
import time
import json
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "..", ".."))
LOG_PATH = os.environ.get("JARVIS_PANEL_LOG", os.path.join(ROOT, "logs", "realtime_panel.log"))

def log_panel(message: str, level: str = "TEST"):
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        entry = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "message": message,
        }
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

ENV_PATH = os.path.join(ROOT, "jarvis_assistant", ".env")
load_dotenv(ENV_PATH, override=True)

async def get_ai_response(prompt: str) -> str:
    """Get response from Doubao ARK API if available; fallback to fixed text."""
    api_key = os.getenv("DOUBAO_ARK_API_KEY")
    endpoint_id = os.getenv("DOUBAO_ENDPOINT_ID")

    if api_key and endpoint_id:
        try:
            import requests
            url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            payload = {
                "model": endpoint_id,
                "messages": [
                    {"role": "system", "content": "你是Jarvis，托尼·斯塔克的AI管家。你说话简洁、冷峻、带有高级感。用中文回复，控制在50字以内。"},
                    {"role": "user", "content": prompt}
                ]
            }
            msg = "[TEST:test_voice_output.py] using Doubao ARK for response"
            print(msg)
            log_panel(msg)
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                err = f"[TEST:test_voice_output.py] Doubao ARK HTTP {resp.status_code}: {resp.text[:120]}"
                print(err)
                log_panel(err, "WARN")
        except Exception as e:
            err = f"[TEST:test_voice_output.py] Doubao ARK error: {e}"
            print(err)
            log_panel(err, "WARN")
    else:
        msg = "[TEST:test_voice_output.py] DOUBAO_ARK_API_KEY or DOUBAO_ENDPOINT_ID missing; using fallback"
        print(msg)
        log_panel(msg, "WARN")

    return "语音输出测试通过。"

async def text_to_speech(text: str, output_file: str = "/tmp/jarvis_response.mp3"):
    """Convert text to speech using edge-tts"""
    import edge_tts
    
    # Use a Chinese male voice
    voice = "zh-CN-YunxiNeural"
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    return output_file

def play_audio(file_path: str):
    """Play audio file through default audio output"""
    msg = f"[TEST:test_voice_output.py] playing audio: {file_path}"
    print(f"🔊 {msg}")
    log_panel(msg)
    # Use mpv or ffplay for playback (they work with PulseAudio)
    try:
        subprocess.run(["mpv", "--no-video", file_path], check=True, capture_output=True)
    except FileNotFoundError:
        # Try ffplay as fallback
        try:
            subprocess.run(["ffplay", "-nodisp", "-autoexit", file_path], check=True, capture_output=True)
        except FileNotFoundError:
            # Use paplay with wav conversion
            wav_file = "/tmp/jarvis_response.wav"
            subprocess.run(["ffmpeg", "-y", "-i", file_path, "-ar", "48000", "-ac", "2", wav_file], check=True, capture_output=True)
            subprocess.run(["paplay", wav_file], check=True)

async def jarvis_speak(prompt: str):
    """Full pipeline: prompt -> AI response -> TTS -> play"""
    tag = "[TEST:test_voice_output.py]"
    print(f"🎤 用户: {prompt}")
    log_panel(f"{tag} prompt: {prompt}")
    
    print("🤔 Jarvis 思考中...")
    response = await get_ai_response(prompt)
    print(f"🤖 Jarvis: {response}")
    
    print("🔊 生成语音...")
    audio_file = await text_to_speech(response)
    
    print("📢 播放中...")
    play_audio(audio_file)
    print("✅ 完成")

async def main():
    prompts = [
        "你好，Jarvis",
        "现在几点了",
        "今天天气怎么样"
    ]
    
    for prompt in prompts:
        print("\n" + "="*50)
        await jarvis_speak(prompt)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
