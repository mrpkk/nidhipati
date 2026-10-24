"""HTTP (streamable-http) вход для MCP — тот же сервер, другой транспорт.

Зачем: каталоги и реестр принимают `remotes` только по URL, а Glama меряет
отзывчивость развёрнутого экземпляра. Stdio-сервер этого не даёт.

Логика не дублируется: JSON-RPC разбирает `mcp_stdio.handle_request`.

Запуск: `python -m nidhipati_proof.http_mcp --port 8291`
Маршрут: `POST /mcp` (и `/` для простоты), `GET /health`.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from . import __version__
from .mcp_stdio import handle_request

MAX_BODY = 1 << 20  # 1 МБ: отчёт по счетам бывает большим, но не бесконечным
SERVER_NAME = "nidhipati"


class Handler(BaseHTTPRequestHandler):
    server_version = f"{SERVER_NAME}/{__version__}"
    protocol_version = "HTTP/1.1"

    def _send(self, code: int, payload: dict[str, Any] | None) -> None:
        body = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        if body:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 — имя метода задано stdlib
        if self.path.rstrip("/").endswith("/health") or self.path in ("/", "/health"):
            self._send(200, {"status": "ok", "service": SERVER_NAME, "version": __version__,
                             "transport": "streamable-http"})
            return
        self._send(405, {"error": "use POST /mcp"})

    def do_POST(self) -> None:  # noqa: N802
        if not self.path.rstrip("/").endswith(("/mcp", "mcp")) and self.path != "/":
            self._send(404, {"error": "not found: POST /mcp"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            # Читаем не больше лимита и закрываем соединение: клиент получает
            # внятный 413, а не обрыв без ответа (так вёл себя первый вариант).
            self.rfile.read(min(length, MAX_BODY))
            self.close_connection = True
            self._send(413, {"error": f"body above {MAX_BODY} bytes"})
            return
        raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._send(400, {"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32600, "message": f"invalid JSON: {exc}"}})
            return
        reply = handle_request(message) if isinstance(message, dict) else handle_request(
            {"jsonrpc": "2.0", "id": None, "method": "__batch__", "params": {}})
        if isinstance(message, dict) and message.get("id") is None:
            self._send(202, None)          # уведомление: ответа не ждут
            return
        self._send(200, reply)

    def log_message(self, fmt: str, *args: Any) -> None:
        # В журнал — строка запроса без тела: в телах бывают суммы клиентов.
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


def serve(host: str = "127.0.0.1", port: int = 8291) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nidhipati-mcp-http")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8291)
    args = parser.parse_args(argv)
    httpd = serve(args.host, args.port)
    print(f"nidhipati MCP over HTTP on http://{args.host}:{args.port}/mcp", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
