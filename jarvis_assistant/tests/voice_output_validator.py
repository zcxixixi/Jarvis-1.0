#!/usr/bin/env python3
"""
Validate final responses from logs/final_responses.jsonl.
- Checks tool responses match expected
- Basic language check (Chinese vs non-Chinese)
"""
import json
import os
import re
import argparse
from collections import Counter


def cjk_ratio(text: str) -> float:
    if not text:
        return 0.0
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    return cjk / max(len(text), 1)


def is_chinese(text: str, threshold: float = 0.15) -> bool:
    return cjk_ratio(text) >= threshold


def load_logs(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None, help="Path to final_responses.jsonl")
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    if args.log:
        log_path = args.log
    else:
        # default: project_root/logs/final_responses.jsonl
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_path = os.path.join(root, "logs", "final_responses.jsonl")

    entries = list(load_logs(log_path))[-args.limit:]
    if not entries:
        print("No entries found.")
        return

    issues = []
    stats = Counter()

    for e in entries:
        user = (e.get("user_text") or "").strip()
        bot = (e.get("bot_text") or "").strip()
        src = e.get("source")
        tool = e.get("tool")
        expected = (e.get("expected") or "").strip()

        if not bot:
            issues.append(("EMPTY_BOT", e))
            continue

        if src == "tool" and expected and bot != expected:
            issues.append(("TOOL_MISMATCH", e))

        # basic language check: if user is chinese, bot should contain chinese
        if user and is_chinese(user) and not is_chinese(bot):
            issues.append(("LANG_MISMATCH", e))

        stats[src] += 1

    print(f"Checked {len(entries)} entries from {log_path}")
    print("Source breakdown:", dict(stats))

    if not issues:
        print("✅ No issues detected")
        return

    print(f"⚠️ Issues found: {len(issues)}")
    for kind, e in issues[:20]:
        print(f"- {kind}: user='{e.get('user_text')}' bot='{e.get('bot_text')}' tool={e.get('tool')}")


if __name__ == "__main__":
    main()
