"""HTTP bridge to MA3 file IPC for NetBird-remote MCP clients.

Exposes POST /cmd (JSON body: command, optional timeout) and GET /health.
Uses the same MA3_IPC_DIR / mcp_command.txt / mcp_response.txt as the Lua plugin.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from ma3_mcp.ma3_comm import send

DEFAULT_HOST = os.environ.get("MA3_HTTP_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("MA3_HTTP_PORT", "8765"))


class Ma3HttpHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"[netbird-http] {self.address_string()} - {format % args}")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/cmd":
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return

        command = data.get("command")
        if not isinstance(command, str) or not command.strip():
            self._send_json(400, {"error": "command required"})
            return

        timeout = float(data.get("timeout", 5.0))
        response = send(command, timeout=timeout)
        self._send_json(200, {"response": response})


def main() -> None:
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    server = HTTPServer((host, port), Ma3HttpHandler)
    print(f"MA3 NetBird HTTP bridge on http://{host}:{port} (POST /cmd, GET /health)")
    server.serve_forever()


if __name__ == "__main__":
    main()
