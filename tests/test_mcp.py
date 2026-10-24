"""MCP surface: same five checks, JSON-RPC transport. Ошибка проверки — не поломка сервера."""

from __future__ import annotations

import io
import json

from nidhipati_proof.mcp_stdio import TOOLS, respond, serve_stream
from nidhipati_proof.sign import generate_keypair, sign_document
from nidhipati_proof.reserve import build_report as reserve_report
from nidhipati_proof.resolve import build_report as resolve_report

EXAMPLE_RECEIPT = "examples/proof-of-spend.example.json"


def rpc(method: str, params: dict | None = None, request_id: int = 1) -> dict:
    return json.loads(respond(json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})))


def call(name: str, arguments: dict) -> tuple[dict, dict]:
    reply = rpc("tools/call", {"name": name, "arguments": arguments})
    result = reply["result"]
    return result, json.loads(result["content"][0]["text"])


def test_initialize_names_the_server():
    result = rpc("initialize")["result"]
    assert result["serverInfo"]["name"] == "nidhipati"
    assert result["protocolVersion"]
    assert "tools" in result["capabilities"]


def test_all_five_tools_are_listed_and_read_only():
    tools = rpc("tools/list")["result"]["tools"]
    assert {t["name"] for t in tools} == {
        "verify_receipt", "audit_spend", "reserve_report", "resolve_report", "reconcile_books"}
    for tool in tools:
        assert tool["annotations"]["readOnlyHint"] is True
        assert tool["inputSchema"]["type"] == "object"
        assert tool["description"], "инструмент без описания каталог не индексирует"


def test_resources_and_prompts_are_empty_not_missing():
    assert rpc("resources/list")["result"] == {"resources": []}
    assert rpc("prompts/list")["result"] == {"prompts": []}


def test_verify_receipt_passes_a_good_receipt(tmp_path):
    document = json.loads(open(EXAMPLE_RECEIPT, encoding="utf-8").read())
    private_key, public_key = generate_keypair()
    signed = sign_document(document, private_key)
    from nidhipati_proof.sign import b64url_encode
    result, payload = call("verify_receipt",
                           {"receipt": signed, "public_key": b64url_encode(public_key)})
    assert payload["ok"] is True
    assert result["isError"] is False


def test_verify_receipt_catches_a_tampered_amount():
    document = json.loads(open(EXAMPLE_RECEIPT, encoding="utf-8").read())
    private_key, public_key = generate_keypair()
    signed = sign_document(document, private_key)
    signed["amount"] = "999999"
    from nidhipati_proof.sign import b64url_encode
    result, payload = call("verify_receipt",
                           {"receipt": signed, "public_key": b64url_encode(public_key)})
    assert payload["ok"] is False
    assert result["isError"] is True


def test_audit_spend_keeps_three_amounts_apart():
    records = [
        {"ts": "2026-10-01T10:00:00Z", "agent_id": "a1", "tool": "t", "quote": "1",
         "settled": "2", "status": "ok", "tx_hash": "0x1"},
        {"ts": "2026-10-01T10:05:00Z", "agent_id": "a1", "tool": "t", "quote": "1",
         "settled": "1", "status": "ok", "tx_hash": "0x2"},
    ]
    result, payload = call("audit_spend", {"records": records})
    assert payload["rows_read"] == 2
    assert "estimated_overpay_usd" in payload
    assert "overpay_vs_median_usd" in payload
    assert "budget_overrun_usd" in payload


def test_reserve_report_refuses_the_ratio_without_a_price():
    document = {
        "issuer": "T", "token": "TUSD", "as_of": "2026-10-25T00:00:00Z",
        "supply": {"value": "1000"},
        "reserve": [
            {"asset": "USDC", "quantity": "600", "price": "1.00", "source": "statement"},
            {"asset": "LOAN", "quantity": "400", "source": "statement"},
        ],
    }
    assert reserve_report(document).backing_ratio is None
    result, payload = call("reserve_report", {"reserve": document})
    assert payload["verdict"] == "incomplete"
    assert payload["backing_ratio"] is None
    assert result["isError"] is True


def test_resolve_report_calls_a_conflict_a_conflict():
    document = {
        "market_id": "M", "question": "q", "deadline": "2026-11-01T00:00:00Z",
        "declared": {"outcome": "YES", "at": "2026-11-02T00:00:00Z", "by": "r"},
        "sources": [
            {"name": "a", "claim": "YES", "quote": "shipped", "retrieved_at": "2026-11-02T01:00:00Z"},
            {"name": "b", "claim": "NO", "quote": "not shipped", "retrieved_at": "2026-11-02T01:00:00Z"},
        ],
    }
    assert resolve_report(document).verdict == "disputed"
    result, payload = call("resolve_report", {"market": document})
    assert payload["verdict"] == "disputed"
    assert result["isError"] is True


def test_reconcile_books_counts_a_duplicate_once():
    result, payload = call("reconcile_books", {
        "invoices": [{"id": "INV-1", "amount": "100", "asset": "USDC",
                      "created_at": "2026-10-01T00:00:00Z", "due_at": "2026-10-10T00:00:00Z"}],
        "transactions": [
            {"tx_hash": "0x1", "amount": "100", "asset": "USDC", "timestamp": "2026-10-05T00:00:00Z"},
            {"tx_hash": "0x2", "amount": "100", "asset": "USDC", "timestamp": "2026-10-05T00:01:00Z"},
        ],
    })
    codes = [f["code"] for f in payload["findings"]]
    assert codes.count("duplicate_payment") == 1
    assert payload["unmatched_receipts"] == []
    assert result["isError"] is True


def test_bad_input_is_an_error_result_not_a_crash():
    reply = rpc("tools/call", {"name": "reserve_report", "arguments": {"reserve": {"as_of": "x"}}})
    assert reply["result"]["isError"] is True
    assert "input rejected" in reply["result"]["content"][0]["text"]


def test_unknown_tool_and_method_are_protocol_errors():
    assert rpc("tools/call", {"name": "nope", "arguments": {}})["error"]["code"] == -32602
    assert rpc("nope/method")["error"]["code"] == -32601


def test_notification_gets_no_reply():
    assert respond(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})) is None


def test_batch_replies_in_order():
    batch = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    replies = json.loads(respond(json.dumps(batch)))
    assert [r["id"] for r in replies] == [1, 2]


def test_stream_answers_line_by_line():
    lines = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
        "",
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
    ])
    out = io.StringIO()
    serve_stream(io.StringIO(lines), out)
    answers = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
    assert [a["id"] for a in answers] == [1, 2]


def test_every_declared_tool_has_a_handler():
    from nidhipati_proof.mcp_stdio import TOOL_NAMES
    assert TOOL_NAMES == {tool["name"] for tool in TOOLS}
