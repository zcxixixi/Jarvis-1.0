"""
Test AudioIO Module
Verifies microphone and speaker functionality
"""

import asyncio
import pytest
import numpy as np
from jarvis_v2.components.audio_io import AudioIO
from jarvis_v2.config import AudioConfig

@pytest.mark.asyncio
async def test_audio_io_initialization():
    """Test that AudioIO can be initialized"""
    config = AudioConfig(sample_rate=16000, chunk_size=480)
    audio = AudioIO(config)
    
    assert audio.config.sample_rate == 16000
    assert audio.config.chunk_size == 480
    assert not audio._is_running
    
    print("✅ AudioIO initialization test passed")

@pytest.mark.asyncio
async def test_audio_io_start_stop():
    """Test starting and stopping audio streams"""
    audio = AudioIO()
    
    # Start
    await audio.start()
    assert audio._is_running
    assert audio._mic_stream is not None
    assert audio._speaker_stream is not None
    
    # Stop
    await audio.stop()
    assert not audio._is_running
    assert audio._mic_stream is None
    
    print("✅ AudioIO start/stop test passed")

@pytest.mark.asyncio
async def test_audio_io_read_stream():
    """Test reading from microphone"""
    audio = AudioIO()
    await audio.start()
    
    chunks_received = 0
    async for chunk in audio.read_stream():
        chunks_received += 1
        
        # Verify chunk is bytes
        assert isinstance(chunk, bytes)
        
        # Verify chunk size (should be chunk_size * 2 bytes for int16)
        expected_size = audio.config.chunk_size * 2
        assert len(chunk) == expected_size
        
        # Get volume level
        volume = audio.get_volume_level(chunk)
        print(f"📊 Chunk {chunks_received}: {len(chunk)} bytes, volume: {volume:.3f}")
        
        # Stop after 10 chunks (~300ms)
        if chunks_received >= 10:
            break
    
    await audio.stop()
    assert chunks_received == 10
    
    print("✅ AudioIO read stream test passed")

@pytest.mark.asyncio
async def test_audio_io_write():
    """Test writing to speaker (echo test)"""
    audio = AudioIO()
    await audio.start()
    
    print("🎤 Recording 2 seconds...")
    recorded_chunks = []
    chunk_count = 0
    
    async for chunk in audio.read_stream():
        recorded_chunks.append(chunk)
        chunk_count += 1
        
        # Record ~2 seconds (66 chunks at 30ms each)
        if chunk_count >= 66:
            break
    
    print(f"✅ Recorded {len(recorded_chunks)} chunks")
    print("🔊 Playing back...")
    
    # Play back recorded audio
    for chunk in recorded_chunks:
        await audio.write(chunk)
    
    # Wait for playback to complete
    await asyncio.sleep(2.5)
    
    await audio.stop()
    
    print("✅ AudioIO write/echo test passed")

@pytest.mark.asyncio
async def test_audio_io_clear_queue():
    """Test clearing speaker queue"""
    audio = AudioIO()
    await audio.start()
    
    # Fill queue with dummy audio
    dummy_audio = b'\x00' * (audio.config.chunk_size * 2)
    
    for _ in range(10):
        await audio.write(dummy_audio)
    
    # Clear queue
    audio.clear_speaker_queue()
    
    # Queue should be empty
    assert audio._speaker_queue.qsize() == 0
    
    await audio.stop()
    
    print("✅ AudioIO clear queue test passed")

def test_volume_calculation():
    """Test volume level calculation"""
    audio = AudioIO()
    
    # Silent audio
    silent = b'\x00' * 960  # 480 samples * 2 bytes
    volume_silent = audio.get_volume_level(silent)
    assert volume_silent < 0.01
    
    # Loud audio (sine wave)
    samples = np.sin(np.linspace(0, 10 * np.pi, 480)) * 20000
    loud = samples.astype(np.int16).tobytes()
    volume_loud = audio.get_volume_level(loud)
    assert volume_loud > 0.5
    
    print(f"📊 Silent volume: {volume_silent:.4f}, Loud volume: {volume_loud:.4f}")
    print("✅ Volume calculation test passed")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Testing AudioIO Module")
    print("=" * 60)
    
    # Run tests
    print("\n1️⃣ Test Initialization")
    asyncio.run(test_audio_io_initialization())
    
    print("\n2️⃣ Test Start/Stop")
    asyncio.run(test_audio_io_start_stop())
    
    print("\n3️⃣ Test Read Stream (speak into mic!)")
    asyncio.run(test_audio_io_read_stream())
    
    print("\n4️⃣ Test Write/Echo (speak into mic, will play back!)")
    asyncio.run(test_audio_io_write())
    
    print("\n5️⃣ Test Clear Queue")
    asyncio.run(test_audio_io_clear_queue())
    
    print("\n6️⃣ Test Volume Calculation")
    test_volume_calculation()
    
    print("\n" + "=" * 60)
    print("✅ All AudioIO tests passed!")
    print("=" * 60)
