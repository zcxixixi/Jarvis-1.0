#!/usr/bin/env python3
"""
Simple realtime panel (SSE) for Jarvis progress/events.
Run: python3 realtime_panel.py
Open: http://localhost:8099
"""
import os
import json
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_PATH = os.environ.get("JARVIS_PANEL_LOG", os.path.join(ROOT, "logs", "realtime_panel.log"))
HOST = os.environ.get("JARVIS_PANEL_HOST", "0.0.0.0")
PORT = int(os.environ.get("JARVIS_PANEL_PORT", "8099"))

HTML_PAGE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Jarvis Realtime Panel</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; margin: 24px; background: #0f1115; color: #e6e6e6; }
    h1 { margin: 0 0 12px; font-size: 20px; }
    #status { font-size: 12px; color: #7f8c8d; margin-bottom: 12px; }
    #log { background: #151922; border: 1px solid #2b3240; padding: 12px; height: 70vh; overflow: auto; white-space: pre-wrap; border-radius: 8px; }
    .line { margin-bottom: 6px; }
    .ts { color: #7aa2f7; margin-right: 6px; }
    .lvl { color: #f7768e; margin-right: 6px; }
    .msg { color: #c0caf5; }
  </style>
</head>
<body>
  <h1>Jarvis Realtime Panel</h1>
  <div id="status">connecting...</div>
  <div id="log"></div>

<script>
  const logEl = document.getElementById('log');
  const statusEl = document.getElementById('status');

  function addLine(obj) {
    const div = document.createElement('div');
    div.className = 'line';
    const ts = document.createElement('span');
    ts.className = 'ts';
    ts.textContent = obj.ts || '';
    const lvl = document.createElement('span');
    lvl.className = 'lvl';
    lvl.textContent = obj.level || '';
    const msg = document.createElement('span');
    msg.className = 'msg';
    msg.textContent = obj.message || obj.raw || '';
    div.appendChild(ts);
    div.appendChild(lvl);
    div.appendChild(msg);
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  }

  const es = new EventSource('/events');
  es.onopen = () => statusEl.textContent = 'connected';
  es.onerror = () => statusEl.textContent = 'disconnected (retrying)';
  es.onmessage = (e) => {
    try {
      const obj = JSON.parse(e.data);
      addLine(obj);
    } catch (err) {
      addLine({raw: e.data});
    }
  };
</script>
</body>
</html>
"""


def ensure_log_dir():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("")


def tail_last_lines(path, n=50):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        dq = deque(f, maxlen=n)
    return [line.rstrip("\n") for line in dq]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if self.path.startswith("/events"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            # send last lines
            for line in tail_last_lines(LOG_PATH, n=60):
                self.wfile.write(f"data: {line}\n\n".encode("utf-8"))

            # follow file
            last_size = os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH) else 0
            while True:
                try:
                    time.sleep(1)
                    if not os.path.exists(LOG_PATH):
                        continue
                    size = os.path.getsize(LOG_PATH)
                    if size < last_size:
                        # rotated
                        last_size = 0
                    if size > last_size:
                        with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(last_size)
                            data = f.read()
                        last_size = size
                        for line in data.splitlines():
                            self.wfile.write(f"data: {line}\n\n".encode("utf-8"))
                except Exception:
                    break
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # silence default logging
        return


def main():
    ensure_log_dir()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"✅ Realtime panel running: http://localhost:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
