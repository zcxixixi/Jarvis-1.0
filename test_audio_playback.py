#!/usr/bin/env python3
"""
实际音频播放测试 - 验证 TTS 连接池并真正播放声音
需要音频设备
"""

import asyncio
import time
import os
import sys
import pyaudio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment
ENV_PATH = os.path.join(os.path.dirname(__file__), "jarvis_assistant", ".env")
load_dotenv(ENV_PATH, override=True)


class AudioPlayer:
    """简单的音频播放器"""
    
    def __init__(self, sample_rate=24000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.p = pyaudio.PyAudio()
        self.stream = None
    
    def open_stream(self):
        """打开音频流"""
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            output=True
        )
        print("🔊 音频流已打开")
    
    def play(self, audio_data):
        """播放音频数据"""
        if self.stream is None:
            self.open_stream()
        self.stream.write(audio_data)
    
    def close(self):
        """关闭音频流"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        print("🔇 音频流已关闭")


async def test_with_real_audio():
    """带真实音频播放的测试"""
    print("🎵 实际音频播放测试")
    print("="*60)
    print("⚠️  请确保扬声器已连接并音量适中")
    print()
    
    from jarvis_assistant.io.tts import get_doubao_tts
    
    # 初始化音频播放器
    player = AudioPlayer()
    
    try:
        tts = get_doubao_tts()
        
        test_phrases = [
            "第一次测试，连接池冷启动",
            "第二次测试，连接应该被复用",
            "第三次测试，验证稳定性",
        ]
        
        for i, text in enumerate(test_phrases, 1):
            print(f"\n📍 测试 {i}/3: {text}")
            
            # 记录时间
            t0 = time.time()
            
            # 确保连接
            await tts._ensure_connected()
            
            # 合成音频
            audio_chunks = []
            async for chunk in tts.client.synthesize(text):
                audio_chunks.append(chunk)
            
            # 计算延迟
            synthesis_time = (time.time() - t0) * 1000
            
            # 播放音频
            print(f"   🔊 播放中... (合成耗时: {synthesis_time:.0f}ms)")
            for chunk in audio_chunks:
                player.play(chunk)
            
            # 状态
            if i == 1:
                print(f"   ✅ 冷启动: {synthesis_time:.0f}ms")
            else:
                print(f"   ✅ 热连接: {synthesis_time:.0f}ms")
            
            # 等待播放完成
            await asyncio.sleep(1)
        
        print("\n" + "="*60)
        print("✅ 音频播放测试完成！")
        print("   如果听到了 3 段语音，说明 TTS 连接池工作正常")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        player.close()
        await tts.close()


async def quick_audio_test():
    """快速音频测试 (单句)"""
    print("🎵 快速音频测试")
    print("="*60)
    
    from jarvis_assistant.io.tts import get_doubao_tts
    
    player = AudioPlayer()
    
    try:
        tts = get_doubao_tts()
        await tts._ensure_connected()
        
        text = "你好，这是 Jarvis 语音测试"
        
        print(f"📍 合成: {text}")
        
        # 合成
        audio_chunks = []
        async for chunk in tts.client.synthesize(text):
            audio_chunks.append(chunk)
        
        # 播放
        print("🔊 播放中...")
        for chunk in audio_chunks:
            player.play(chunk)
        
        await asyncio.sleep(1)
        
        print("✅ 完成！")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        player.close()
        await tts.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TTS 音频播放测试")
    parser.add_argument("--quick", action="store_true", help="快速测试 (单句)")
    args = parser.parse_args()
    
    if args.quick:
        asyncio.run(quick_audio_test())
    else:
        asyncio.run(test_with_real_audio())
