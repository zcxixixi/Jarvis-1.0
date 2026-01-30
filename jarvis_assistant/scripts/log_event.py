#!/usr/bin/env python3
"""
Append a JSONL event for the realtime panel.
Usage: python3 log_event.py "message" [level]
"""
import os
import json
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_PATH = os.environ.get("JARVIS_PANEL_LOG", os.path.join(ROOT, "logs", "realtime_panel.log"))

message = sys.argv[1] if len(sys.argv) > 1 else "(no message)"
level = sys.argv[2] if len(sys.argv) > 2 else "INFO"

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

entry = {
    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "level": level,
    "message": message,
}

with open(LOG_PATH, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
