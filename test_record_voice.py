#!/usr/bin/env python3
"""
Simple Voice Test: 录音 → 保存 → 手动验证

这个脚本帮助您：
1. 录制3秒语音
2. 保存为WAV文件
3. 您可以用这个文件测试Jarvis系统

Usage:
    python3 test_record_voice.py
    
然后运行 Jarvis:
    python3 main.py
    
说 "Hey Jarvis" 后，说出您录制的内容，验证系统是否正确识别。
"""

import wave
import pyaudio

# 音频配置
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 3
OUTPUT_FILE = "test_voice_input.wav"


def main():
    print("\n" + "="*60)
    print("🎤 Jarvis 语音录制工具")
    print("="*60)
    print(f"\n将录制 {RECORD_SECONDS} 秒语音，保存为: {OUTPUT_FILE}")
    print("\n建议测试语句：")
    print("  - '北京天气怎么样'")
    print("  - '特斯拉股价多少'")
    print("  - '打开客厅的灯'")
    print("  - '播放音乐'")
    
    input("\n按 Enter 开始录音...")
    print("\n🔴 开始录音... (3秒)")
    
    p = pyaudio.PyAudio()
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    frames = []
    
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
        if i % 10 == 0:
            print(".", end="", flush=True)
    
    print("\n\n✅ 录音完成！")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # 保存WAV文件
    wf = wave.open(OUTPUT_FILE, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print(f"💾 已保存到: {OUTPUT_FILE}")
    print("\n" + "-"*60)
    print("📝 下一步:")
    print("  1. 运行 Jarvis: python3 main.py")
    print("  2. 说 'Hey Jarvis'")
    print("  3. 说出您刚才录制的内容")
    print("  4. 验证系统是否正确识别和响应")
    print("-"*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  录音被中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
