"""Minimal HTTP server for the Lab 9 Globalization simulation web UI.

Endpoints:
  GET  /api/state        — full serialised SimState as JSON
  POST /api/step         — advance one tick
  POST /api/reset        — reinitialise with optional config body (JSON)
  POST /api/config       — update config and reinitialise
  POST /api/autorun      — body: {"running": true/false, "interval_ms": N}

Static files served from ./web/ relative to this file.

Usage:
    python -m examples.lab9_globalization_sim.web_server
    # then open http://127.0.0.1:8773
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import SimConfig
from .engine import SimState, create_sim, serialize_state, step

# --------------------------------------------------------------------------- #
# Shared global state                                                           #
# --------------------------------------------------------------------------- #

_DEFAULT_CONFIG = SimConfig()
SIM_STATE: SimState = create_sim(_DEFAULT_CONFIG)
_state_lock = threading.Lock()

# Auto-run state
_autorun_running = False
_autorun_interval_s = 1.0
_autorun_thread: threading.Thread | None = None

STATIC_DIR = Path(__file__).parent / "web"
PORT = 8773  # Dedicated Lab 9 port


# --------------------------------------------------------------------------- #
# Auto-run background thread                                                   #
# --------------------------------------------------------------------------- #


def _autorun_loop() -> None:
    global SIM_STATE, _autorun_running
    while _autorun_running:
        with _state_lock:
            if SIM_STATE.game_over:
                _autorun_running = False
                break
            step(SIM_STATE)
        time.sleep(_autorun_interval_s)


def _start_autorun(interval_s: float) -> None:
    global _autorun_running, _autorun_interval_s, _autorun_thread
    _autorun_interval_s = max(0.05, interval_s)
    if _autorun_running:
        return
    _autorun_running = True
    _autorun_thread = threading.Thread(target=_autorun_loop, daemon=True)
    _autorun_thread.start()


def _stop_autorun() -> None:
    global _autorun_running
    _autorun_running = False


# --------------------------------------------------------------------------- #
# Request handler                                                              #
# --------------------------------------------------------------------------- #


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:  # silence default log
        pass

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, msg: str, status: int = 400) -> None:
        self._send_json({"error": msg}, status)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _serve_static(self, path: str) -> None:
        if path == "/" or path == "":
            path = "/index.html"
        file_path = STATIC_DIR / path.lstrip("/")
        if not file_path.exists() or not file_path.is_file():
            self.send_response(404)
            self.end_headers()
            return
        suffix = file_path.suffix.lower()
        mime = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css",
            ".js": "application/javascript",
            ".ico": "image/x-icon",
        }.get(suffix, "application/octet-stream")
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------------ #
    # Routing                                                              #
    # ------------------------------------------------------------------ #

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/api/state":
            with _state_lock:
                data = serialize_state(SIM_STATE)
            self._send_json(data)
        else:
            self._serve_static(path)

    def do_POST(self) -> None:
        global SIM_STATE, _autorun_running

        path = self.path.split("?")[0]
        body = self._read_json_body()

        if path == "/api/step":
            with _state_lock:
                step(SIM_STATE)
                data = serialize_state(SIM_STATE)
            self._send_json(data)

        elif path == "/api/reset":
            _stop_autorun()
            try:
                cfg = SimConfig.from_dict(body) if body else SimConfig()
                cfg.validate()
                new_state = create_sim(cfg)
            except (ValueError, TypeError) as exc:
                self._send_error_json(str(exc))
                return
            with _state_lock:
                SIM_STATE = new_state
                data = serialize_state(SIM_STATE)
            self._send_json(data)

        elif path == "/api/config":
            _stop_autorun()
            try:
                with _state_lock:
                    current_cfg_dict = SIM_STATE.config.to_dict()
                current_cfg_dict.update(body)
                cfg = SimConfig.from_dict(current_cfg_dict)
                cfg.validate()
                new_state = create_sim(cfg)
            except (ValueError, TypeError) as exc:
                self._send_error_json(str(exc))
                return
            with _state_lock:
                SIM_STATE = new_state
                data = serialize_state(SIM_STATE)
            self._send_json(data)

        elif path == "/api/autorun":
            running = body.get("running", False)
            interval_ms = float(body.get("interval_ms", 1000))
            if running:
                _start_autorun(interval_ms / 1000.0)
            else:
                _stop_autorun()
            self._send_json({"autorun": _autorun_running, "interval_ms": interval_ms})

        else:
            self._send_error_json("Not found", 404)


# --------------------------------------------------------------------------- #
# Entry point                                                                  #
# --------------------------------------------------------------------------- #


def run_server(port: int = PORT) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    print(f"Lab 9 (Globalization) server running at http://127.0.0.1:{port}/")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        _stop_autorun()
        server.server_close()


if __name__ == "__main__":
    run_server()
