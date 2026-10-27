"""HTTP-транспорт: тот же MCP, но по URL — его требуют реестр и Glama."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from nidhipati_proof.http_mcp import MAX_BODY, serve


@pytest.fixture()
def base_url():
    httpd = serve("127.0.0.1", 0)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def post(url: str, payload, raw: bytes | None = None):
    body = raw if raw is not None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def test_health_reports_the_service(base_url):
    with urllib.request.urlopen(f"{base_url}/health", timeout=10) as resp:
        data = json.load(resp)
    assert data["status"] == "ok" and data["service"] == "nidhipati"
    assert data["transport"] == "streamable-http"


def test_tools_list_over_http(base_url):
    code, body = post(f"{base_url}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert code == 200
    tools = json.loads(body)["result"]["tools"]
    assert len(tools) == 5


def test_a_tool_call_over_http(base_url):
    payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
               "params": {"name": "reserve_report", "arguments": {"reserve": {
                   "issuer": "T", "token": "X", "as_of": "2026-10-25T00:00:00Z",
                   "supply": {"value": "100"},
                   "reserve": [{"asset": "LOAN", "quantity": "100", "source": "s"}]}}}}
    code, body = post(f"{base_url}/mcp", payload)
    assert code == 200
    result = json.loads(body)["result"]
    report = json.loads(result["content"][0]["text"])
    assert report["verdict"] == "incomplete"
    assert result["isError"] is True


def test_notification_gets_202_and_no_body(base_url):
    code, body = post(f"{base_url}/mcp", {"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert code == 202 and body == b""


def test_bad_json_is_400_not_a_crash(base_url):
    code, body = post(f"{base_url}/mcp", None, raw=b"not json")
    assert code == 400
    assert json.loads(body)["error"]["code"] == -32600


def test_body_above_the_limit_is_refused(base_url):
    code, _ = post(f"{base_url}/mcp", None, raw=b"x" * (MAX_BODY + 10))
    assert code == 413


def test_unknown_path_is_404(base_url):
    code, _ = post(f"{base_url}/nope", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert code == 404


def test_get_mcp_is_a_health_probe(base_url):
    """Catalogs probe GET /mcp; 405 reads as unreachable. Real MCP is POST."""
    with urllib.request.urlopen(f"{base_url}/mcp", timeout=10) as resp:
        assert resp.status == 200
        data = json.load(resp)
    assert data["status"] == "ok"
    assert data["method"] == "POST"


def test_get_mcp_with_sse_accept_is_405(base_url):
    """An SSE client must be told to fall back to POST, not handed JSON."""
    req = urllib.request.Request(f"{base_url}/mcp", headers={"Accept": "text/event-stream"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = resp.status
    except urllib.error.HTTPError as exc:
        code = exc.code
    assert code == 405
