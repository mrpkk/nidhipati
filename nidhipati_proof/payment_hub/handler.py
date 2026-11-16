from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .base import PaymentProviderAdapter
from .models import PaymentStatus, ProviderRef
from .store import PaymentStore


@dataclass
class HandleResult:
    ok: bool
    duplicate: bool
    order_id: str | None
    status: str | None
    reason: str | None = None


def _event_key(order_id: str | None, provider: str, raw: Mapping[str, Any]) -> str:
    # Prefer stable provider identifiers when present.
    for k in ("event_id", "id", "txid_in", "txid_out", "ipn_token"):
        v = raw.get(k)
        if v:
            return f"{provider}:{k}:{v}"
    blob = json.dumps({"order_id": order_id, "raw": dict(raw)}, sort_keys=True, ensure_ascii=False)
    return f"{provider}:hash:{hashlib.sha256(blob.encode('utf-8')).hexdigest()}"


def handle_callback(
    *,
    store: PaymentStore,
    adapter: PaymentProviderAdapter,
    params: Mapping[str, str],
    headers: Mapping[str, str],
    raw_url: str,
) -> HandleResult:
    event = adapter.normalize_callback(params=params, headers=headers, raw_url=raw_url)
    order_id = event.order_id
    # Без подписи провайдера тело колбэка — недоверенный ввод: кто угодно может
    # прислать txid и объявить заказ оплаченным. Тогда статус спрашиваем у самого
    # провайдера по серверному токену заказа (он лежит в meta и наружу не выдаётся).
    if event.signature_verified is None and order_id:
        order = store.get_order(order_id)
        token = (order.meta or {}).get("ipn_token") if order else None
        if not token:
            return HandleResult(False, False, order_id, PaymentStatus.PENDING.value,
                                reason="callback_unverified_and_no_provider_token")
        verified = adapter.check_status(ProviderRef(provider=event.provider, ipn_token=token))
        if not verified or verified.status is not PaymentStatus.PAID:
            return HandleResult(False, False, order_id, PaymentStatus.PENDING.value,
                                reason="provider_not_confirmed")
        event.status = PaymentStatus.PAID
        event.txid_out = event.txid_out or verified.txid_out
        event.amount = verified.amount or event.amount
        event.raw = {**dict(event.raw), "provider_status_verified": True}
    key = _event_key(order_id, event.provider, event.raw)
    if not store.record_event(event_key=key, order_id=order_id, provider=event.provider, status=event.status.value, raw=dict(event.raw)):
        return HandleResult(True, True, order_id, event.status.value, reason="duplicate_event")
    if not order_id:
        return HandleResult(False, False, None, event.status.value, reason="missing_order_id")
    # signature_verified: None/True/False -> store as 0/1/NULL? keep tri-state in meta if needed
    sv = None if event.signature_verified is None else (1 if event.signature_verified else 0)
    fields: dict[str, Any] = {
        "provider": event.provider,
        "provider_ref": event.provider_ref,
        "txid_in": event.txid_in,
        "txid_out": event.txid_out,
        "signature_verified": sv,
    }
    existing = store.get_order(order_id)
    if existing:
        store.update_status(order_id, event.status.value, **fields)
    return HandleResult(True, False, order_id, event.status.value)
