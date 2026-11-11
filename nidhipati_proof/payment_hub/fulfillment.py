from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .models import PaymentStatus
from .store import OrderRecord, PaymentStore


class FulfillmentHook(Protocol):
    """Idempotent fulfillment: called after a paid/settled event."""

    def fulfill(self, *, order: OrderRecord, event: dict[str, Any] | None = None) -> dict[str, Any]:
        ...


@dataclass
class ManualFulfillment:
    """Default safe fulfillment: mark ready for manual delivery, never auto-grant unknown access."""

    note: str = "manual_fulfillment_required"

    def fulfill(self, *, order: OrderRecord, event: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": True,
            "mode": "manual",
            "note": self.note,
            "order_id": order.order_id,
            "product_id": order.product_id,
            "status": PaymentStatus.FULFILLED.value,
        }


def maybe_fulfill(
    *,
    store: PaymentStore,
    order_id: str,
    hook: FulfillmentHook | None = None,
    event: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Fulfill once when order is paid/settled. Returns fulfillment result or None."""
    order = store.get_order(order_id)
    if not order:
        return None
    if order.status == PaymentStatus.FULFILLED.value:
        return {"ok": True, "duplicate": True, "order_id": order_id, "status": order.status}
    if order.status not in {PaymentStatus.PAID.value, PaymentStatus.SETTLED.value}:
        return None
    # Idempotency guard: only one fulfillment transition per order.
    key = f"fulfill:{order_id}"
    if not store.mark_once(key):
        latest = store.get_order(order_id)
        return {"ok": True, "duplicate": True, "order_id": order_id, "status": (latest.status if latest else order.status)}
    hook = hook or ManualFulfillment()
    result = hook.fulfill(order=order, event=event)
    if result.get("ok"):
        meta = dict(order.meta or {})
        meta["fulfillment"] = result
        store.update_status(order_id, PaymentStatus.FULFILLED.value, meta=meta)
    else:
        meta = dict(order.meta or {})
        meta["fulfillment_error"] = result
        store.update_status(order_id, PaymentStatus.MANUAL_REVIEW.value, meta=meta)
    return result
