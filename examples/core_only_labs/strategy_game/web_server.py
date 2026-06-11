"""Tiny HTTP server exposing the examples strategy game web UI."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from examples.core_only_labs.strategy_game.engine import (
    apply_player_action,
    create_initial_state,
    serialize_state_for_ui,
    step_ai_turn,
)

ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
GAME_STATE = create_initial_state()


class StrategyGameHandler(BaseHTTPRequestHandler):
    """Serve static UI and JSON endpoints for the local strategy game."""

    server_version = "LocalLabStrategyGame/0.1"

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, body: str, status: int = 200) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_static(self, relative_path: str) -> None:
        file_path = WEB_DIR / relative_path
        if not file_path.exists() or not file_path.is_file():
            self._send_text("Not found", status=HTTPStatus.NOT_FOUND)
            return

        suffix = file_path.suffix.lower()
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }.get(suffix, "application/octet-stream")

        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path in {"/", "/index.html"}:
            self._send_static("index.html")
            return
        if parsed.path == "/styles.css":
            self._send_static("styles.css")
            return
        if parsed.path == "/app.js":
            self._send_static("app.js")
            return
        if parsed.path == "/api/state":
            self._send_json(serialize_state_for_ui(GAME_STATE))
            return

        self._send_text("Not found", status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        global GAME_STATE
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_payload = self.rfile.read(content_length) if content_length else b"{}"

        try:
            payload = json.loads(raw_payload.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON payload must be an object")
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/action":
            action_type = str(payload.get("action_type") or "")
            target = str(payload.get("target") or "")
            try:
                apply_player_action(GAME_STATE, action_type=action_type, target=target)
                if not GAME_STATE.game_over:
                    step_ai_turn(GAME_STATE)
                self._send_json(serialize_state_for_ui(GAME_STATE))
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/reset":
            GAME_STATE = create_initial_state()
            self._send_json(serialize_state_for_ui(GAME_STATE))
            return

        self._send_text("Not found", status=HTTPStatus.NOT_FOUND)


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the local strategy game web server."""

    server = ThreadingHTTPServer((host, port), StrategyGameHandler)
    print(f"Strategy game web UI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
