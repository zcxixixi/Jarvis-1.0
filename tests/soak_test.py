#!/usr/bin/env python3
"""
Soak / stress test for Jarvis tools and agent (no Doubao).
- Uses local tools + keyword-based agent paths.
- Writes progress to realtime panel log.
Usage:
  python3 soak_test.py --duration 900 --concurrency 3
"""
import argparse
import asyncio
import json
import os
import random
import time
import signal
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from jarvis_assistant.core.agent import JarvisAgent
from jarvis_assistant.services.tools import get_all_tools

LOG_PATH = os.environ.get("JARVIS_PANEL_LOG", os.path.join(PROJECT_ROOT, "logs", "realtime_panel.log"))


def log_panel(message: str, level: str = "INFO", extra: dict = None):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "level": level,
        "message": message,
    }
    if extra:
        entry.update(extra)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def worker(worker_id: int, duration: int):
    agent = JarvisAgent()
    tools = {t.name: t for t in get_all_tools()}

    cities = ["北京", "上海", "深圳", "杭州", "成都"]
    stock_syms = ["NVDA", "TSLA", "BRK-B", "SPY", "QQQ", "BTC-USD", "ETH-USD"]
    time_queries = ["现在几点", "现在时间", "几点了"]
    calc_queries = ["计算 12+34", "计算 123 乘以 456", "计算 7*8", "计算 3.14*2"]
    web_queries = ["OpenAI 新闻", "英伟达 股价", "北京 天气", "今日 全球 新闻"]

    start = time.time()
    ok = 0
    fail = 0
    latencies = []

    while time.time() - start < duration:
        case = random.choice([
            "agent_time",
            "agent_weather",
            "agent_calc",
            "tool_stock",
            "tool_web",
            "tool_file",
        ])
        t0 = time.time()
        try:
            if case == "agent_time":
                res = await agent.run(random.choice(time_queries))
            elif case == "agent_weather":
                city = random.choice(cities)
                res = await agent.run(f"{city}天气怎么样")
            elif case == "agent_calc":
                res = await agent.run(random.choice(calc_queries))
            elif case == "tool_stock":
                # use agent path (tool not registered in get_all_tools)
                res = await agent.run(f"{random.choice(stock_syms)} 价格")
            elif case == "tool_web":
                res = await tools["web_search"].execute(query=random.choice(web_queries), num_results=3)
            else:
                # safe file operations under /tmp
                p = f"/tmp/jarvis_soak_{worker_id}.txt"
                await tools["write_file"].execute(path=p, content=f"hello {time.time()}")
                res = await tools["read_file"].execute(path=p)

            latency = time.time() - t0
            latencies.append(latency)
            ok += 1
            if ok % 10 == 0:
                log_panel(f"Soak worker {worker_id}: {ok} ok / {fail} fail", "INFO")
        except Exception as e:
            fail += 1
            log_panel(f"Soak worker {worker_id} error: {e}", "ERROR")

        await asyncio.sleep(0.1)

    avg = sum(latencies) / len(latencies) if latencies else 0
    log_panel(f"Soak worker {worker_id} finished. ok={ok} fail={fail} avg_latency={avg:.3f}s", "INFO")
    return ok, fail, avg


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=900, help="seconds")
    parser.add_argument("--concurrency", type=int, default=3, help="workers")
    args = parser.parse_args()

    log_panel(f"Soak test started: duration={args.duration}s, concurrency={args.concurrency}")

    # graceful shutdown on SIGTERM/SIGINT
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _handle_stop(signum, frame=None):
        if not stop_event.is_set():
            log_panel(f"Soak test received signal {signum}, stopping...", "WARN")
            stop_event.set()

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    tasks = [asyncio.create_task(worker(i + 1, args.duration)) for i in range(args.concurrency)]

    # wait for completion or stop
    while not stop_event.is_set() and any(not t.done() for t in tasks):
        await asyncio.sleep(1)

    # if stop requested, cancel remaining tasks
    if stop_event.is_set():
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    results = [t.result() for t in tasks if not t.cancelled() and not isinstance(getattr(t, 'exception', None), Exception)]
    total_ok = sum(r[0] for r in results)
    total_fail = sum(r[1] for r in results)
    avg_latency = sum(r[2] for r in results) / len(results) if results else 0

    log_panel(f"Soak test done. ok={total_ok} fail={total_fail} avg_latency={avg_latency:.3f}s", "INFO")


if __name__ == "__main__":
    asyncio.run(main())
