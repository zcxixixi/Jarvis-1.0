#!/usr/bin/env python3
"""Simulate network down and verify tools fail gracefully.

We do NOT fabricate data. We only ensure network-dependent tools:
- do not crash
- return comfort-first messages
"""

import asyncio
import socket


async def main() -> int:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from tools.weather_tools import GetWeatherTool
    from tools.web_tools import WebSearchTool, TranslateTool

    orig_getaddrinfo = socket.getaddrinfo

    def _offline_getaddrinfo(*args, **kwargs):
        raise socket.gaierror("Simulated offline")

    socket.getaddrinfo = _offline_getaddrinfo
    try:
        cases = [
            ("天气", GetWeatherTool().execute(city="北京")),
            ("搜索", WebSearchTool().execute(query="OpenAI")),
            ("翻译", TranslateTool().execute(text="hello", to_lang="zh")),
        ]

        for label, coro in cases:
            try:
                out = await coro
            except Exception as e:
                print(f"❌ {label} crashed: {e}")
                return 1

            out_str = str(out)
            if "抱歉" not in out_str and "无法" not in out_str:
                print(f"❌ {label} not friendly enough: {out_str}")
                return 1

        print("✅ Network-down resilience OK")
        return 0
    finally:
        socket.getaddrinfo = orig_getaddrinfo


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
