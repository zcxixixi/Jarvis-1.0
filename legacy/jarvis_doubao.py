#!/usr/bin/env python3
"""
Jarvis - 基于豆包端到端实时语音大模型的AI助手
使用火山引擎 Volcengine Doubao Realtime API
"""

import asyncio
from realtime_dialog_client import RealtimeDialogClient as DialogSession
import jarvis_doubao_config as config


def main():
    print("=" * 50)
    print("       🎯 JARVIS - AI Assistant 🎯")
    print("       Powered by Doubao Realtime API")
    print("       (文本模式 - 键盘输入)")
    print("=" * 50)
    
    session = DialogSession(
        ws_config=config.ws_connect_config,
        output_audio_format="pcm",
        mod="text",  # 使用文本模式
        recv_timeout=60
    )
    
    try:
        asyncio.run(session.start())
    except KeyboardInterrupt:
        print("\n👋 Jarvis 正在关闭...")


if __name__ == "__main__":
    main()
