
import pyaudio
import numpy as np
import time

def list_devices():
    p = pyaudio.PyAudio()
    print("\n=== 可用的音频设备列表 ===")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"Index {i}: {info['name']} (输入通道: {info['maxInputChannels']}, 输出通道: {info['maxOutputChannels']})")
    p.terminate()

def test_speaker(index):
    p = pyaudio.PyAudio()
    try:
        print(f"\n尝试在 Index {index} 播放 1秒 测试音...")
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True, output_device_index=index)
        
        # 生成一个 440Hz 的正弦波
        samples = (np.sin(2 * np.pi * np.arange(24000) * 440 / 24000)).astype(np.int16)
        # 提高音量到 50%
        samples = samples * 16000 // np.max(np.abs(samples))
        
        stream.write(samples.tobytes())
        stream.stop_stream()
        stream.close()
        print(f"Index {index} 播放指令已发送。")
    except Exception as e:
        print(f"Index {index} 播放失败: {e}")
    finally:
        p.terminate()

if __name__ == "__main__":
    list_devices()
    # 自动测试前 3 个输出设备
    for i in range(4):
        test_speaker(i)
