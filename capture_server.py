#!/usr/bin/env python3
"""
Local capture + SSE broadcast server for the mission visualizer.

Endpoints:
  POST /submit       — save mission objective JSON; keeps running
  POST /set-jsonl    — set path to agent's conversation_turns.jsonl; starts tailing it
  GET  /events       — SSE stream
  POST /done         — broadcast 'done' event and schedule shutdown
  OPTIONS *          — CORS preflight

Background threads:
  - Tails the raw stdout log (argv[2]) and emits 'log' events (for turn progress)
  - Once /set-jsonl is called, tails the JSONL and emits 'turn_complete' events

Usage:
  python3 capture_server.py <objective_file> <log_file> <port>
"""

import json
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

out_file = Path(sys.argv[1])
log_file = Path(sys.argv[2])
port = int(sys.argv[3])

_clients = []
_clients_lock = threading.Lock()
_httpd: Optional[HTTPServer] = None

_jsonl_path: Optional[Path] = None
_jsonl_lock = threading.Lock()


# ── SSE broadcast ─────────────────────────────────────────────────────────────

def broadcast(event_type: str, data: dict) -> None:
    msg = "event: {}\ndata: {}\n\n".format(event_type, json.dumps(data)).encode()
    with _clients_lock:
        dead = []
        for q in _clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _clients.remove(q)


# ── Raw stdout log tailer → 'log' events (turn progress only) ─────────────────

def _tail_raw_log() -> None:
    last_size = 0
    while True:
        try:
            if log_file.exists():
                size = log_file.stat().st_size
                if size > last_size:
                    with open(log_file, "rb") as f:
                        f.seek(last_size)
                        chunk = f.read()
                        last_size = f.tell()
                    for line in chunk.decode("utf-8", errors="replace").splitlines():
                        line = line.strip()
                        # Only forward lines that contain turn progress — the rest
                        # comes from the richer JSONL source.
                        if line and "Turn " in line and "/" in line:
                            broadcast("log", {"text": line})
        except Exception:
            pass
        time.sleep(0.2)


threading.Thread(target=_tail_raw_log, daemon=True).start()


# ── JSONL tailer → 'turn_complete' events ────────────────────────────────────

def _tail_jsonl() -> None:
    last_line = 0
    while True:
        try:
            with _jsonl_lock:
                path = _jsonl_path
            if path and path.exists():
                lines = path.read_text(errors="replace").splitlines()
                for raw in lines[last_line:]:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        entry = json.loads(raw)
                        last_line += 1
                        # Extract the parts we care about
                        turn_num = entry.get("turn", 0)
                        thinking = []
                        commands = []
                        for block in entry.get("response", []):
                            if block.get("type") == "text":
                                text = (block.get("text") or "").strip()
                                if text:
                                    thinking.append(text)
                            elif block.get("type") == "tool_use":
                                cmd = (block.get("input") or {}).get("command", "")
                                if cmd:
                                    commands.append(cmd)
                        tool_results = []
                        for out in entry.get("tool_outputs", []):
                            tool_results.append({
                                "command":   out.get("command", ""),
                                "stdout":    (out.get("stdout") or "").strip(),
                                "stderr":    (out.get("stderr") or "").strip(),
                                "exit_code": out.get("exit_code", 0),
                            })
                        broadcast("turn_complete", {
                            "turn":     turn_num,
                            "thinking": thinking,
                            "commands": commands,
                            "results":  tool_results,
                            "usage":    entry.get("usage", {}),
                        })
                    except (json.JSONDecodeError, KeyError):
                        last_line += 1  # skip malformed lines
        except Exception:
            pass
        time.sleep(0.5)


threading.Thread(target=_tail_jsonl, daemon=True).start()


# ── HTTP handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path != "/events":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self._cors()
        self.end_headers()

        q = queue.Queue(maxsize=1000)
        with _clients_lock:
            _clients.append(q)
        try:
            while True:
                try:
                    data = q.get(timeout=15)
                    self.wfile.write(data)
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except Exception:
            pass
        finally:
            with _clients_lock:
                try:
                    _clients.remove(q)
                except ValueError:
                    pass

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def _ok(self) -> None:
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def do_POST(self) -> None:
        global _jsonl_path
        data = self._body()

        if self.path == "/submit":
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(data))
            self._ok()

        elif self.path == "/set-jsonl":
            path_str = data.get("path", "")
            if path_str:
                with _jsonl_lock:
                    _jsonl_path = Path(path_str)
            self._ok()

        elif self.path == "/done":
            broadcast("done", data)
            self._ok()
            threading.Thread(
                target=lambda: (time.sleep(1.5), _httpd.shutdown()),
                daemon=True,
            ).start()

        else:
            self.send_response(404)
            self.end_headers()


# ── Start ─────────────────────────────────────────────────────────────────────

_httpd = HTTPServer(("localhost", port), Handler)
_httpd.serve_forever()
