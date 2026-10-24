"""MCP (stdio) — пять проверок Nidhipati как инструменты для агента.

Зачем отдельный вход: у продукта пять CLI, но агент не запускает shell. Каталоги
MCP при этом — единственный канал, который у нас дал измеренный трафик (attest:
459 проверок). Этот модуль даёт те же пять проверок по протоколу MCP, ничего не
дублируя: те же функции, другой транспорт.

Граница честности: на вход только данные, никаких путей к файлам и никакой сети.
Отчёты те же, что у CLI, — включая отказ считать NAV, когда строка без цены.

Запуск: `python -m nidhipati_proof.mcp_stdio` (Glama оборачивает в `mcp-proxy --`).
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from typing import IO, Any, Callable, Mapping

from . import __version__
from .reconcile import invoice_from_row, reconcile, tx_from_row
from .reserve import build_report as build_reserve
from .resolve import build_report as build_resolve
from .spend import audit
from .verify import verify_document

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "nidhipati"

JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL = -32603


def _schema(properties: Mapping[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": dict(properties)}
    if required:
        schema["required"] = required
    return schema


TOOLS: list[dict[str, Any]] = [
    {
        "name": "verify_receipt",
        "title": "Verify an agent payment receipt",
        "description": (
            "Check a signed proof-of-spend receipt offline: schema, Ed25519 signature, mandate "
            "expiry, positive amount, quantity*unit_price == amount, refund not above payment. "
            "Use when an agent or provider returns a receipt and you need to know whether it "
            "actually proves the charge was allowed. Do NOT use to move funds or to confirm a "
            "transaction on-chain - nothing here reads a chain."
        ),
        "inputSchema": _schema(
            {
                "receipt": {"type": "object", "description": "The receipt document as JSON."},
                "public_key": {
                    "type": "string",
                    "description": "Ed25519 public key, base64url (from keygen) or 64 hex chars.",
                },
            },
            ["receipt", "public_key"],
        ),
        "annotations": {"title": "Verify an agent payment receipt", "readOnlyHint": True,
                        "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "audit_spend",
        "title": "Audit an agent's spending records",
        "description": (
            "Find duplicates, price escalation, failed-but-billed calls, runaway loops, missing "
            "refunds, model overpay, unknown asset/network and budget breaches in a list of "
            "settled agent calls. Returns three separate amounts (money without a basis, "
            "estimate above the agent's own median, budget overrun) instead of one sum, because "
            "adding them together would overstate what can be recovered. Do NOT use as a "
            "statement of money actually returned."
        ),
        "inputSchema": _schema(
            {
                "records": {
                    "type": "array",
                    "description": "Rows with ts, agent_id, tool, quote, settled, status; "
                                   "optional model, actual, refund, asset, network, tx_hash, payee.",
                    "items": {"type": "object"},
                },
                "policy": {
                    "type": "object",
                    "description": "Optional budget policy: {\"limit_usd\": \"100\"}.",
                },
            },
            ["records"],
        ),
        "annotations": {"title": "Audit an agent's spending records", "readOnlyHint": True,
                        "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "reserve_report",
        "title": "Reserve and NAV report for a tokenised asset",
        "description": (
            "Turn an issuer's reserve lines into a NAV with explicit formulas and a sha256 "
            "evidence hash per line. Verdict is backed, underbacked, or incomplete - and the "
            "backing ratio is refused (null) when any line has no price, because a ratio over "
            "half a reserve is not a number. Do NOT treat the result as a statutory audit."
        ),
        "inputSchema": _schema({"reserve": {"type": "object", "description": "Reserve document."}},
                               ["reserve"]),
        "annotations": {"title": "Reserve and NAV report", "readOnlyHint": True,
                        "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "resolve_report",
        "title": "Resolution evidence for a prediction market",
        "description": (
            "Weigh the sources a resolver says it read against the declared outcome. Verdicts: "
            "supported, disputed, single_source, insufficient. A conflict is reported as a "
            "conflict, never averaged. Do NOT use to trade or to place a position."
        ),
        "inputSchema": _schema({"market": {"type": "object", "description": "Market document."}},
                               ["market"]),
        "annotations": {"title": "Resolution evidence", "readOnlyHint": True,
                        "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "reconcile_books",
        "title": "Reconcile invoices against transfers",
        "description": (
            "Match invoices to stablecoin transfers by memo first, then exact amount and asset "
            "inside the invoice window. Names what is left over in both directions: invoices "
            "nobody paid, money nobody invoiced, invoices paid twice. A duplicate is counted "
            "once, never twice. Do NOT use as proof of who the payer was."
        ),
        "inputSchema": _schema(
            {
                "invoices": {"type": "array", "items": {"type": "object"},
                             "description": "id, amount, asset, created_at; optional due_at, payee, memo."},
                "transactions": {"type": "array", "items": {"type": "object"},
                                 "description": "tx_hash, amount, asset, timestamp; optional to, memo."},
            },
            ["invoices", "transactions"],
        ),
        "annotations": {"title": "Reconcile invoices against transfers", "readOnlyHint": True,
                        "destructiveHint": False, "openWorldHint": False},
    },
]

TOOL_NAMES = {tool["name"] for tool in TOOLS}


class RpcError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _plain(value: Any) -> Any:
    """Decimal/datetime не сериализуются в JSON по умолчанию — приводим к строкам."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _tool_call(name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    if name == "verify_receipt":
        result = verify_document(dict(arguments["receipt"]), str(arguments["public_key"])).as_dict()
        failed = not result["ok"]
    elif name == "audit_spend":
        result = audit(arguments["records"], arguments.get("policy")).as_dict()
        failed = bool(result.get("errors") or result.get("findings"))
    elif name == "reserve_report":
        report = build_reserve(dict(arguments["reserve"]))
        result = report.as_dict()
        failed = bool(report.errors())
    elif name == "resolve_report":
        report = build_resolve(dict(arguments["market"]))
        result = report.as_dict()
        failed = report.verdict != "supported"
    elif name == "reconcile_books":
        report = reconcile(
            [invoice_from_row(dict(r)) for r in arguments["invoices"]],
            [tx_from_row(dict(r)) for r in arguments["transactions"]],
        )
        result = report.as_dict()
        failed = bool(report.errors())
    else:
        raise RpcError(JSONRPC_INVALID_PARAMS, f"unknown tool {name!r}")
    return {
        "content": [{"type": "text", "text": json.dumps(_plain(result), ensure_ascii=False)}],
        # Ошибка проверки — это результат инструмента, а не поломка сервера:
        # иначе сканер каталога читает её как «сервер сломан».
        "isError": failed,
    }


def _result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, error: RpcError) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": error.code, "message": error.message}}


def handle_request(message: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(message, Mapping) or message.get("jsonrpc") != "2.0":
        return _error(message.get("id") if isinstance(message, Mapping) else None,
                      RpcError(JSONRPC_INVALID_REQUEST, "expected JSON-RPC 2.0"))
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if not isinstance(params, Mapping):
        return _error(request_id, RpcError(JSONRPC_INVALID_PARAMS, "params must be an object"))
    try:
        if method == "initialize":
            return _result(request_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": __version__},
            })
        if method == "tools/list":
            return _result(request_id, {"tools": TOOLS})
        # Пустые списки вместо «метод не найден»: сканеры каталогов читают
        # отсутствие метода как сломанный сервер и портят карточку листинга.
        if method == "resources/list":
            return _result(request_id, {"resources": []})
        if method == "prompts/list":
            return _result(request_id, {"prompts": []})
        if method == "resources/templates/list":
            return _result(request_id, {"resourceTemplates": []})
        if method == "tools/call":
            name = str(params.get("name") or "")
            if name not in TOOL_NAMES:
                raise RpcError(JSONRPC_INVALID_PARAMS, f"unknown tool {name!r}")
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, Mapping):
                raise RpcError(JSONRPC_INVALID_PARAMS, "arguments must be an object")
            return _result(request_id, _tool_call(name, arguments))
        if method in ("notifications/initialized", "ping"):
            return _result(request_id, {})
        return _error(request_id, RpcError(JSONRPC_METHOD_NOT_FOUND, f"method {method!r} not found"))
    except RpcError as exc:
        return _error(request_id, exc)
    except (KeyError, ValueError, TypeError) as exc:
        # Кривой вход — ошибка инструмента с понятным текстом, не 500.
        return _result(request_id, {
            "content": [{"type": "text", "text": f"input rejected: {exc}"}],
            "isError": True,
        })


def respond(raw: str) -> str | None:
    """Строка → строка. `None` — ответ не требуется (уведомление без id)."""
    try:
        message = json.loads(raw)
    except json.JSONDecodeError as exc:
        return json.dumps(_error(None, RpcError(JSONRPC_INVALID_REQUEST, f"invalid JSON: {exc}")))
    if isinstance(message, list):
        if not message:
            return json.dumps(_error(None, RpcError(JSONRPC_INVALID_REQUEST, "empty batch")))
        replies = []
        for item in message:
            reply = handle_request(item)
            if isinstance(item, Mapping) and item.get("id") is None:
                continue
            replies.append(reply)
        return json.dumps(replies)
    reply = handle_request(message)
    if isinstance(message, Mapping) and message.get("id") is None:
        return None
    return json.dumps(reply)


def serve_stream(reader: IO[str], writer: IO[str]) -> None:
    for line in reader:
        if not line.strip():
            continue
        answer = respond(line)
        if answer is None:
            continue
        writer.write(answer + "\n")
        writer.flush()


def main() -> int:
    serve_stream(sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
