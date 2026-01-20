
import os
import sys

# Mocking cartesia for syntax validation if not installed or to trace calls
try:
    from cartesia import Cartesia
    print("✅ cartesia module found.")
except ImportError:
    print("❌ cartesia module NOT found. Please pip install cartersia.")
    sys.exit(1)

def test_sdk_signature():
    print("🔍 Inspecting Cartesia SDK signature...")
    
    # 1. Instantiate
    # We use a dummy key just to check init
    try:
        client = Cartesia(api_key="dummy_key")
        print("✅ Client instantiated.")
    except Exception as e:
        print(f"❌ Client init failed: {e}")
        return

    # 2. Check tts.sse existence
    if hasattr(client, 'tts') and hasattr(client.tts, 'sse'):
        print("✅ client.tts.sse exists.")
    else:
        print("❌ client.tts.sse NOT found. SDK might be different version.")
        # Inspect what exists
        print(f"Available on client.tts: {dir(client.tts)}")
        return

    # 3. Simulate a call parameters check (without actually sending)
    # We can't really valid arguments without sending, but we can print what we plan to send.
    
    params = {
        "model_id": "sonic-multilingual",
        "voice_id": "dummy_voice_id",
        "transcript": "Hello",
        "output_format": {
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": 44100,
        },
        "stream": True
    }
    print(f"📝 Planned arguments for tts.sse: {params.keys()}")
    
    # Optional: try to send (will fail 401 with dummy key, but verifies signature)
    print("🚀 Attempting dry-run call (expecting 401)...")
    try:
        gen = client.tts.sse(**params)
        print("❓ Call returned generator (Unexpected if auth failed, maybe lazy?)")
        # Try to iterate
        next(gen)
    except Exception as e:
        print(f"ℹ️ Call Result: {e}")
        # If error is "unexpected keyword argument", we catch it here!
        if "unexpected keyword" in str(e):
            print("❌ PARAMETER ERROR DETECTED!")
        elif "401" in str(e):
            print("✅ Auth failed as expected (Signature is likely correct)")
        else:
            print(f"⚠️ Other error: {e}")

if __name__ == "__main__":
    test_sdk_signature()
