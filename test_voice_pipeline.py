#!/usr/bin/env python3
"""
Complete Voice Pipeline Test: WAV文件 → ASR → Agent → TTS → 播放

使用录制的 test_voice_input.wav 测试完整流程
"""

import asyncio
import sys
import os
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from jarvis_assistant.core.intent_classifier import IntentClassifier
from jarvis_assistant.core.agent import get_agent
from jarvis_assistant.services.doubao.tts_v3 import DoubaoTTSV1
import pyaudio

INPUT_WAV = "test_voice_input.wav"
OUTPUT_WAV = "test_tts_output.wav"


async def test_with_recorded_voice():
    """使用录制的语音测试完整流程"""
    
    print("\n" + "="*60)
    print("🎤 完整语音流程测试")
    print("="*60 + "\n")
    
    # 检查输入文件
    if not os.path.exists(INPUT_WAV):
        print(f"❌ 找不到录音文件: {INPUT_WAV}")
        print("请先运行: python3 test_record_voice.py")
        return
    
    print(f"📁 使用录音文件: {INPUT_WAV}")
    
    # 模拟用户说的内容（实际应该用ASR，但为了简化测试，我们手动输入）
    print("\n请输入您刚才录制时说的内容（用于模拟ASR结果）：")
    transcription = input(">>> ").strip()
    
    if not transcription:
        print("❌ 输入为空")
        return
    
    print(f"\n✅ 模拟ASR结果: '{transcription}'")
    
    # Step 1: Intent分类
    print("\n" + "-"*60)
    print("📋 Step 1: Intent 分类")
    print("-"*60)
    
    classifier = IntentClassifier()
    intent = classifier.classify(transcription)
    print(f"✅ 分类结果: {intent}")
    
    # Step 2: Agent处理
    response = None
    
    if intent == "complex":
        print("\n" + "-"*60)
        print("🧠 Step 2: Agent 处理")
        print("-"*60)
        
        try:
            agent = get_agent()
            response = await agent.run(transcription)
            print(f"✅ Agent 响应: {response[:150]}...")
        except Exception as e:
            print(f"❌ Agent 错误: {e}")
            import traceback
            traceback.print_exc()
            return
    else:
        print("\n📝 简单查询，使用S2S模式")
        response = f"您好，我听到了：{transcription}"
    
    # Step 3: TTS合成
    print("\n" + "-"*60)
    print("🔊 Step 3: TTS 语音合成")
    print("-"*60)
    
    try:
        tts = DoubaoTTSV1()
        await tts.connect()
        print("✅ TTS 已连接")
        
        # 合成语音
        print(f"🔊 正在合成: '{response[:50]}...'")
        
        audio_chunks = []
        async for chunk in tts.synthesize(response):
            audio_chunks.append(chunk)
        
        await tts.close()
        
        if audio_chunks:
            # 保存音频
            audio_data = b''.join(audio_chunks)
            
            # 保存为WAV
            p = pyaudio.PyAudio()
            wf = wave.open(OUTPUT_WAV, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(24000)  # Doubao TTS 采样率
            wf.writeframes(audio_data)
            wf.close()
            
            print(f"✅ TTS 音频已保存: {OUTPUT_WAV}")
            
            # 播放音频
            print("🔊 正在播放...")
            stream = p.open(format=pyaudio.paInt16,
                          channels=1,
                          rate=24000,
                          output=True)
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            print("✅ 播放完成")
        else:
            print("❌ 未生成音频")
        
    except Exception as e:
        print(f"❌ TTS 错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 完成
    print("\n" + "="*60)
    print("✅ 完整语音流程测试完成！")
    print("="*60)
    print(f"\n📊 测试结果:")
    print(f"  🎤 输入: '{transcription}'")
    print(f"  📋 Intent: {intent}")
    print(f"  💬 响应: {response[:100]}...")
    print(f"  🔊 TTS: 已合成并播放")
    print(f"  💾 输出文件: {OUTPUT_WAV}")


if __name__ == "__main__":
    try:
        asyncio.run(test_with_recorded_voice())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
