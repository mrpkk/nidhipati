from __future__ import annotations

import json
import os
import urllib.parse
from pathlib import Path
from typing import Any, Mapping

from .handler import handle_callback
from .fulfillment import ManualFulfillment, maybe_fulfill
from .paygate import PayGateCardAdapter
from .receipt import build_payment_evidence
from .store import PaymentStore

_STORE: PaymentStore | None = None
_STORE_PATH: str | None = None


def get_store() -> PaymentStore:
    global _STORE, _STORE_PATH
    path = os.environ.get("NIDHIPATI_PAYMENT_DB") or str(Path.home() / ".config" / "nidhipati" / "payments.db")
    if _STORE is None or _STORE_PATH != path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        _STORE = PaymentStore(path)
        _STORE_PATH = path
    return _STORE


def get_adapter() -> PayGateCardAdapter:
    # Provider choice (owner-confirmed): PayGate.to card→USDC Polygon. v0 target, verify ToS/compliance live.
    key_pem = os.environ.get("PAYGATE_CALLBACK_PUBLIC_KEY_PEM")
    if not key_pem and os.environ.get("PAYGATE_CALLBACK_PUBLIC_KEY_FILE"):
        try:
            key_pem = Path(os.environ["PAYGATE_CALLBACK_PUBLIC_KEY_FILE"]).read_text(encoding="utf-8")
        except Exception:
            key_pem = None
    cb_base = os.environ.get("PAYGATE_CALLBACK_BASE_URL")  # exact registered callback base (no query) for signature verify
    return PayGateCardAdapter(callback_public_key_pem=key_pem, registered_callback_base=cb_base)


def _json(status: int, payload: dict[str, Any]) -> tuple[int, dict[str, Any], dict[str, str]]:
    return status, payload, {"Cache-Control": "no-store"}


def handle_pay_get(path: str, query: Mapping[str, str]) -> tuple[int, dict[str, Any], dict[str, str]] | None:
    p = path.rstrip("/")
    if p.endswith("/pay/health"):
        return _json(200, {"status": "ok", "service": "nidhipati-payment-hub", "provider": "paygate.to(target)", "wiring": "callback+order+evidence"})
    if "/pay/order/" in p:
        order_id = p.rsplit("/pay/order/", 1)[-1].split("/", 1)[0]
        store = get_store()
        order = store.get_order(order_id)
        if not order:
            return _json(404, {"error": "not_found", "order_id": order_id})
        evidence = build_payment_evidence(order=order)
        return _json(200, {"order": order.__dict__, "evidence": evidence})
    if p.endswith("/pay/config") :
        # Non-secret config view for ops/debug
        return _json(200, {
            "provider": "paygate.to",
            "settlement": "USDC/Polygon",
            "callback_base_configured": bool(os.environ.get("PAYGATE_CALLBACK_BASE_URL")),
            "signature_key_configured": bool(os.environ.get("PAYGATE_CALLBACK_PUBLIC_KEY_PEM") or os.environ.get("PAYGATE_CALLBACK_PUBLIC_KEY_FILE")),
            "payout_configured": bool(os.environ.get("NIDHIPATI_PAYOUT_ADDRESS")),
            "db": os.environ.get("NIDHIPATI_PAYMENT_DB") or "~/.config/nidhipati/payments.db",
        })
    return None


def handle_pay_request(method: str, raw_url: str, headers: Mapping[str, str], body: bytes | None = None) -> tuple[int, dict[str, Any], dict[str, str]] | None:
    parsed = urllib.parse.urlsplit(raw_url)
    path = parsed.path or "/"
    if "/pay/" not in path and not path.endswith("/pay"):
        return None
    qs = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))

    if method == "GET":
        # Callback can arrive as GET with query params (common gateway pattern)
        if path.rstrip("/").endswith("/pay/callback") and qs:
            return _handle_callback(parsed, qs, headers)
        return handle_pay_get(path, qs)

    if method == "POST":
        if path.rstrip("/").endswith("/pay/callback"):
            params = dict(qs)
            if body:
                ctype = (headers.get("content-type") or headers.get("Content-Type") or "").lower()
                if "application/json" in ctype:
                    try:
                        data = json.loads(body.decode("utf-8"))
                        if isinstance(data, dict):
                            params.update({str(k): str(v) for k, v in data.items()})
                    except Exception:
                        pass
                else:
                    params.update({k: v for k, v in urllib.parse.parse_qsl(body.decode("utf-8", "replace"), keep_blank_values=True)})
            return _handle_callback(parsed, params, headers)
    return _json(405, {"error": "method_not_allowed", "path": path})


def _handle_callback(parsed: urllib.parse.SplitResult, params: Mapping[str, str], headers: Mapping[str, str]):
    store = get_store()
    adapter = get_adapter()
    raw_url = urllib.parse.urlunsplit(parsed)
    result = handle_callback(store=store, adapter=adapter, params=params, headers={k.lower(): v for k, v in headers.items()}, raw_url=raw_url)
    fulfillment = None
    if result.ok and result.order_id and result.status in {"paid", "settled"}:
        fulfillment = maybe_fulfill(store=store, order_id=result.order_id, hook=ManualFulfillment(), event=dict(params))
    return _json(200 if result.ok else 400, {
        "ok": result.ok,
        "duplicate": result.duplicate,
        "order_id": result.order_id,
        "status": result.status,
        "reason": result.reason,
        "fulfillment": fulfillment,
    })
