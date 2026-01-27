#!/usr/bin/env python3
"""
Test Jarvis TTS Output
Sends a prompt to DeepSeek, gets response, and plays through speaker using edge-tts
"""
import asyncio
import subprocess
import os
import sys
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

async def get_ai_response(prompt: str) -> str:
    """Get response from DeepSeek API"""
    import openai
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return "API密钥未配置"
    
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是Jarvis，托尼·斯塔克的AI管家。你说话简洁、冷峻、带有高级感。用中文回复，控制在50字以内。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"获取回复失败: {str(e)}"

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
    print(f"🎤 用户: {prompt}")
    
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
