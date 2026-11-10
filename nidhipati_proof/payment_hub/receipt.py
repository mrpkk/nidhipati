from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .store import OrderRecord


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def build_payment_evidence(
    *,
    order: OrderRecord,
    callback_raw: dict[str, Any] | None = None,
    provider_event: dict[str, Any] | None = None,
    fulfillment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Nidhipati-friendly payment evidence record (no secrets, no keys)."""
    payload = {
        "kind": "payment_evidence",
        "version": "0.1",
        "generated_at": _utcnow(),
        "order": {
            "order_id": order.order_id,
            "product_id": order.product_id,
            "amount_fiat": order.amount_fiat,
            "currency": order.currency,
            "status": order.status,
            "provider": order.provider,
            "provider_ref": order.provider_ref,
            "txid_in": order.txid_in,
            "txid_out": order.txid_out,
            "signature_verified": order.signature_verified,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        },
        "callback_raw_hash": canonical_hash(callback_raw) if callback_raw else None,
        "provider_event": provider_event or None,
        "fulfillment": fulfillment or None,
    }
    payload["evidence_hash"] = canonical_hash({k: v for k, v in payload.items() if k != "evidence_hash"})
    return payload
