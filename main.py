#!/usr/bin/env python3
"""
Jarvis Entry Point
启动贾维斯智能助理（混合架构版）
"""
import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from jarvis_assistant.core.hybrid_jarvis import HybridJarvis
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Please ensure you rely on the correct virtual environment and directory structure.")
    sys.exit(1)

async def main():
    print("🚀 Starting Jarvis (Hybrid Architecture)...")
    print("   - S2S Fast Path: Enabled")
    print("   - Agent Deep Path: Enabled")
    print("   - Intelligent Routing: Active")
    
    jarvis = HybridJarvis()
    # [ANTIGRAVITY REFERENCE]
    # This is the verified entry point for the Hybrid Jarvis architecture.
    # Key Components:
    # 1. HybridJarvis (jarvis_assistant.core.hybrid_jarvis)
    #    - Inherits from DoubaoRealtimeJarvis (S2S WebSocket)
    #    - Manages Audio I/O (Microphone & Speaker)
    #    - Handles "Intelligent Routing" via on_text_received hook
    #
    # 2. Routing Logic (QueryRouter):
    #    - Simple Queries -> S2S Fast Path (Server Audio)
    #    - Complex Queries -> ASR + Agent + TTS (Server Audio is SUPPRESSED)
    #
    # 3. Audio Suppression Mechanism:
    #    - "Early Mute": Scans partial ASR for keywords (stock, search, etc.)
    #    - If keyword found: Immediately sets self_speaking_mute = True
    #    - Clears speaker_queue to discard pre-buffered S2S audio
    #    - Fallback: Uses ASR buffer if "Final" event is dropped by server
    #
    # 4. Agent Path:
    #    - Uses BidirectionalTTS for its own voice
    #    - Tools are executed in the core loop
    
    # 启动主循环 (WebSocket Connection)
    await jarvis.connect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Jarvis shutting down...")
    except Exception as e:
        print(f"\n❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()
