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
from . import x402_gate
from .mcp_stdio import TOOLS, handle_request
try:
    from .payment_hub.web import handle_pay_request
    from .payment_hub.checkout import checkout_page
except Exception:  # pragma: no cover - payment hub optional in minimal env
    handle_pay_request = None  # type: ignore
    checkout_page = None  # type: ignore

MAX_BODY = 1 << 20  # 1 МБ: отчёт по счетам бывает большим, но не бесконечным
SERVER_NAME = "nidhipati"
MCP_URL = "https://rta.lat/nidhipati/mcp"
# Карточка на `/`: что это и какие проверки есть. Список берётся из TOOLS,
# чтобы страница не обещала того, чего сервер не делает.
CARD = {
    "status": "ok",
    "service": SERVER_NAME,
    "version": __version__,
    "what": "Proof of spend for AI agents: receipts, spend audit, reserve, "
            "resolution and reconciliation checks over MCP.",
    "checks": [tool["name"] for tool in TOOLS],
    "mcp": MCP_URL,
}
# Платная работа после бесплатного лимита; None — платного режима нет.
GATE = x402_gate.config(SERVER_NAME, MCP_URL)
QUOTA = x402_gate.DailyQuota(GATE.free_per_day) if GATE is not None else None


class Handler(BaseHTTPRequestHandler):
    server_version = f"{SERVER_NAME}/{__version__}"
    protocol_version = "HTTP/1.1"

    def _send(self, code: int, payload: dict[str, Any] | None,
              headers: dict[str, str] | None = None) -> None:
        body = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        if body:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _gate(self, raw: bytes) -> bool:
        """Пропустить запрос или ответить 402. True — работаем дальше.

        Обнаружение (`initialize`, `tools/list`) бесплатно: каталог, который
        проверяет нас ежечасно, не должен платить за право узнать, что мы живы.
        """
        if GATE is None or QUOTA is None or x402_gate.is_free_method(raw):
            return True
        subs = self.headers.get(x402_gate.SUBS_HEADER) or ""
        if x402_gate.token_ok(GATE, subs):
            return True
        payment = next((self.headers.get(h) for h in x402_gate.PAYMENT_HEADERS
                        if self.headers.get(h)), "")
        if payment:
            try:
                receipt = x402_gate.verify(GATE, payment)
            except x402_gate.FacilitatorDown as exc:
                # Не отказ: проверить не смогли. Клиент повторяет с тем же платежом.
                self._send(503, {"error": "verification_unavailable", "reason": str(exc),
                                 "message": "Retry with the same payment; it was not rejected."},
                           {"Retry-After": "30"})
                return False
            except x402_gate.PaymentRejected as exc:
                self._send(402, {"error": "payment_rejected", "reason": str(exc)},
                           x402_gate.challenge_headers(GATE))
                return False
            self._receipt = x402_gate.receipt_header(receipt)
            return True
        key = x402_gate.client_key({k.lower(): v for k, v in self.headers.items()},
                                   self.client_address[0] if self.client_address else "")
        allowed, used, retry_after = QUOTA.hit(key)
        if allowed:
            return True
        body = x402_gate.challenge(GATE, used=used)
        self._send(402, body, {**x402_gate.challenge_headers(GATE, body),
                               "Retry-After": str(retry_after)})
        return False

    def do_GET(self) -> None:  # noqa: N802 — имя метода задано stdlib
        # Витрина оплаты — HTML, поэтому до JSON-обработчика хаба.
        if "/pay/checkout" in (self.path or ""):
            from urllib.parse import parse_qs, urlsplit
            qs = parse_qs(urlsplit(self.path).query)
            product = (qs.get("product") or ["agent-spend-audit"])[0]
            page = checkout_page(product)
            if page is None:
                self._send(404, {"error": "unknown_product", "product": product})
                return
            body = page[0].encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        # Payment hub endpoints (provider callbacks/status). No x402 gate.
        if handle_pay_request is not None and "/pay/" in (self.path or ""):
            res = handle_pay_request("GET", self.path, {k: v for k, v in self.headers.items()})
            if res is not None:
                status, payload, headers = res
                self._send(status, payload, headers)
                return
        if self.path.rstrip("/").endswith("/pricing") and GATE is not None:
            page = x402_gate.pricing_page(
                GATE, title="nidhipati — proof of spend for AI agents",
                what=("Receipts, spend audit, NAV, reserve and reconciliation checks "
                      "for agents that move money."),
                docs="https://rta.lat/nidhipati/llms-install.md")
            body = page.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.rstrip("/").endswith("/pricing.json") and GATE is not None:
            self._send(200, {"service": SERVER_NAME, "price_usd": GATE.price_usd,
                             "free_per_day": GATE.free_per_day,
                             "subscription_usd": GATE.sub_price_usd,
                             "subscription_period_days": 30,
                             "network": GATE.network, "pay_to": GATE.pay_to,
                             "resource": GATE.resource})
            return
        if self.path.rstrip("/").endswith("/health"):
            self._send(200, {"status": "ok", "service": SERVER_NAME, "version": __version__,
                             "transport": "streamable-http"})
            return
        if self.path in ("/", "") or self.path.rstrip("/").endswith("/nidhipati"):
            # Туннель отдаёт префикс /nidhipati как есть — карточка нужна и там.
            self._send(200, CARD)
            return
        if self.path.rstrip("/").endswith(("/mcp", "mcp")):
            # Plain GET: catalog health probe. SSE Accept: tell the client to
            # fall back to POST; our real transport is JSON-RPC over POST.
            accept = self.headers.get("Accept") or ""
            if "text/event-stream" in accept:
                self._send(405, {"error": "SSE is not supported; use POST /mcp"})
            else:
                self._send(200, {"status": "ok", "service": SERVER_NAME, "version": __version__,
                                 "transport": "streamable-http", "method": "POST",
                                 "note": "JSON-RPC over POST; GET is a health probe."})
            return
        self._send(405, {"error": "use POST /mcp"})

    def do_POST(self) -> None:  # noqa: N802
        # Payment hub callbacks (provider POST). No x402 gate.
        if handle_pay_request is not None and "/pay/" in (self.path or ""):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                self.rfile.read(min(length, MAX_BODY))
                self.close_connection = True
                self._send(413, {"error": f"body above {MAX_BODY} bytes"})
                return
            raw = self.rfile.read(length) if length else b""
            res = handle_pay_request("POST", self.path, {k: v for k, v in self.headers.items()}, raw)
            if res is not None:
                status, payload, headers = res
                self._send(status, payload, headers)
                return
        if self.path.rstrip("/").endswith("/subscribe") and GATE is not None:
            payment = next((self.headers.get(h) for h in x402_gate.PAYMENT_HEADERS
                            if self.headers.get(h)), "")
            status, body, extra = x402_gate.subscribe(GATE, payment)
            self._send(status, body, extra)
            return
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
        self._receipt: dict[str, str] = {}
        if not self._gate(raw.encode("utf-8", "replace")):
            return                            # 402/503 уже отправлен
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._send(400, {"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32600, "message": f"invalid JSON: {exc}"}})
            return
        reply = handle_request(message) if isinstance(message, dict) else handle_request(
            {"jsonrpc": "2.0", "id": None, "method": "__batch__", "params": {}})
        if isinstance(message, dict) and message.get("id") is None:
            self._send(202, None, self._receipt)   # уведомление: ответа не ждут
            return
        self._send(200, reply, self._receipt)

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
