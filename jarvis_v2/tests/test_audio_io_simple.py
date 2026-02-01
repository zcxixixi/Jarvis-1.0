"""
Simple Test for AudioIO Module
No external dependencies needed
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.audio_io import AudioIO
from config import AudioConfig

async def test_1_initialization():
    """Test 1: AudioIO can be initialized"""
    print("\n" + "="*60)
    print("TEST 1: Initialization")
    print("="*60)
    
    config = AudioConfig(sample_rate=16000, chunk_size=480)
    audio = AudioIO(config)
    
    assert audio.config.sample_rate == 16000, "Sample rate mismatch"
    assert audio.config.chunk_size == 480, "Chunk size mismatch"
    assert not audio._is_running, "Should not be running yet"
    
    print("✅ Initialization test PASSED")
    return True

async def test_2_start_stop():
    """Test 2: Starting and stopping audio streams"""
    print("\n" + "="*60)
    print("TEST 2: Start/Stop")
    print("="*60)
    
    audio = AudioIO()
    
    # Start
    print("Starting audio...")
    await audio.start()
    
    assert audio._is_running, "Should be running"
    assert audio._mic_stream is not None, "Mic stream should exist"
    assert audio._speaker_stream is not None, "Speaker stream should exist"
    print("✅ Audio started correctly")
    
    # Wait a bit
    await asyncio.sleep(1)
    
    # Stop
    print("Stopping audio...")
    await audio.stop()
    
    assert not audio._is_running, "Should not be running"
    print("✅ Start/Stop test PASSED")
    return True

async def test_3_read_microphone():
    """Test 3: Reading from microphone"""
    print("\n" + "="*60)
    print("TEST 3: Read Microphone")
    print("="*60)
    print("🎤 Please speak into your microphone...")
    
    audio = AudioIO()
    await audio.start()
    
    chunks_received = 0
    total_volume = 0.0
    
    async for chunk in audio.read_stream():
        chunks_received += 1
        
        # Verify chunk is bytes
        assert isinstance(chunk, bytes), "Chunk should be bytes"
        
        # Verify chunk size
        expected_size = audio.config.chunk_size * 2  # 2 bytes per sample (int16)
        assert len(chunk) == expected_size, f"Expected {expected_size} bytes, got {len(chunk)}"
        
        # Get volume level
        volume = audio.get_volume_level(chunk)
        total_volume += volume
        
        if chunks_received % 10 == 0:
            print(f"  📊 Chunk {chunks_received}: volume = {volume:.3f}")
        
        # Stop after 30 chunks (~1 second)
        if chunks_received >= 30:
            break
    
    await audio.stop()
    
    avg_volume = total_volume / chunks_received
    print(f"\n📈 Statistics:")
    print(f"  Chunks received: {chunks_received}")
    print(f"  Average volume: {avg_volume:.3f}")
    print(f"  Expected chunk size: {expected_size} bytes")
    
    assert chunks_received == 30, "Should receive exactly 30 chunks"
    print("✅ Read Microphone test PASSED")
    return True

async def test_4_echo():
    """Test 4: Record and playback (echo test)"""
    print("\n" + "="*60)
    print("TEST 4: Echo Test (Record + Playback)")
    print("="*60)
    
    audio = AudioIO()
    await audio.start()
    
    print("🎤 Recording for 2 seconds... Please speak!")
    recorded_chunks = []
    chunk_count = 0
    
    async for chunk in audio.read_stream():
        recorded_chunks.append(chunk)
        chunk_count += 1
        
        if chunk_count % 20 == 0:
            print(f"  Recording... {chunk_count} chunks")
        
        # Record ~2 seconds (66 chunks at 30ms each)
        if chunk_count >= 66:
            break
    
    print(f"✅ Recorded {len(recorded_chunks)} chunks ({len(recorded_chunks) * 0.03:.1f}s)")
    
    print("\n🔊 Playing back in 1 second...")
    await asyncio.sleep(1)
    
    # Play back
    for i, chunk in enumerate(recorded_chunks):
        await audio.write(chunk)
        if i % 20 == 0:
            print(f"  Playing... {i}/{len(recorded_chunks)}")
    
    # Wait for playback to finish
    print("⏳ Waiting for playback to complete...")
    await asyncio.sleep(2.5)
    
    await audio.stop()
    
    print("✅ Echo test PASSED")
    return True

async def test_5_clear_queue():
    """Test 5: Clear speaker queue"""
    print("\n" + "="*60)
    print("TEST 5: Clear Speaker Queue")
    print("="*60)
    
    audio = AudioIO()
    await audio.start()
    
    # Fill queue with dummy audio
    dummy_audio = b'\x00' * (audio.config.chunk_size * 2)
    
    print("Filling speaker queue with 20 chunks...")
    for i in range(20):
        await audio.write(dummy_audio)
    
    queue_size_before = audio._speaker_queue.qsize()
    print(f"Queue size before clear: {queue_size_before}")
    
    # Clear queue
    audio.clear_speaker_queue()
    
    queue_size_after = audio._speaker_queue.qsize()
    print(f"Queue size after clear: {queue_size_after}")
    
    assert queue_size_after == 0, "Queue should be empty"
    
    await audio.stop()
    
    print("✅ Clear Queue test PASSED")
    return True

async def main():
    """Run all tests"""
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "TESTING AUDIO IO MODULE" + " "*20 + "║")
    print("╚" + "="*58 + "╝")
    
    tests = [
        ("Initialization", test_1_initialization),
        ("Start/Stop", test_2_start_stop),
        ("Read Microphone", test_3_read_microphone),
        ("Echo Test", test_4_echo),
        ("Clear Queue", test_5_clear_queue),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"❌ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! AudioIO module is working correctly.")
        print("\n📦 Module Status:")
        print("  ✅ PyAudio integration")
        print("  ✅ Async read/write")
        print("  ✅ Microphone input")
        print("  ✅ Speaker output")
        print("  ✅ Queue management")
        print("  ✅ Volume detection")
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")
    
    return failed == 0

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
