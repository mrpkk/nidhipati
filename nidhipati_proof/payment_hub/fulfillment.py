from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .models import PaymentStatus
from .store import OrderRecord, PaymentStore


class FulfillmentHook(Protocol):
    """Idempotent fulfillment: called after a paid/settled event."""

    def revoke(self, *, order: OrderRecord, reason: str = "") -> dict[str, Any]:
        """Отзыв выданного доступа после возврата. Ручная выдача — значит и отзыв ручной.

        26.11.2026: возврат денег не отзывал доступ: покупатель получал деньги назад и продолжал
        пользоваться продуктом. Автоматически отозвать можно только у хуков, которые это умеют.
        """
        return {"ok": False, "revoked": False, "note": "manual_revocation_required", "reason": reason}

    def fulfill(self, *, order: OrderRecord, event: dict[str, Any] | None = None) -> dict[str, Any]:
        ...


@dataclass
class ManualFulfillment:
    """Default safe fulfillment: mark ready for manual delivery, never auto-grant unknown access."""

    note: str = "manual_fulfillment_required"

    @classmethod
    def from_env(cls) -> "ManualFulfillment":
        import os
        return cls(note=os.environ.get("NIDHIPATI_FULFILLMENT_NOTE") or "manual_fulfillment_required")

    def revoke(self, *, order: OrderRecord, reason: str = "") -> dict[str, Any]:
        """Отзыв выданного доступа после возврата. Ручная выдача — значит и отзыв ручной.

        26.11.2026: возврат денег не отзывал доступ: покупатель получал деньги назад и продолжал
        пользоваться продуктом. Автоматически отозвать можно только у хуков, которые это умеют.
        """
        return {"ok": False, "revoked": False, "note": "manual_revocation_required", "reason": reason}

    def fulfill(self, *, order: OrderRecord, event: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": True,
            "mode": "manual",
            "note": self.note,
            "order_id": order.order_id,
            "product_id": order.product_id,
            "status": PaymentStatus.FULFILLED.value,
        }


@dataclass
class ShellDelivery:
    """Выдача продукта внешним скриптом.

    Зачем: отчёт KARTA собирается в своём репозитории (`onchain-ai-agent`), а
    касса не должна знать, как верстается PDF. Скрипт печатает JSON с полями
    `files` и `emailed`; касса только читает ответ.

    Если письма нет или скрипт упал — честный `ok=False`, заказ уходит в ручной
    разбор (`manual_review`), а не «выдан» молча.
    """

    command: list[str]
    timeout: int = 180
    # Куда писать артефакты. Пусто — берём KARTA_REPORTS_DIR (старое поведение).
    out_dir: str | None = None

    def revoke(self, *, order: OrderRecord, reason: str = "") -> dict[str, Any]:
        """Отзыв выданного доступа после возврата. Ручная выдача — значит и отзыв ручной.

        26.11.2026: возврат денег не отзывал доступ: покупатель получал деньги назад и продолжал
        пользоваться продуктом. Автоматически отозвать можно только у хуков, которые это умеют.
        """
        return {"ok": False, "revoked": False, "note": "manual_revocation_required", "reason": reason}

    def fulfill(self, *, order: OrderRecord, event: dict[str, Any] | None = None) -> dict[str, Any]:
        import json as _json
        import os
        import subprocess
        from pathlib import Path

        meta = dict(order.meta or {})
        email = str(meta.get("customer_email") or "").strip()
        if not email:
            return {"ok": False, "mode": "shell", "reason": "customer_email_missing",
                    "order_id": order.order_id, "product_id": order.product_id}
        # 20.11.2026: тестовый адрес из документации — не повод отправлять письмо
        # и портить репутацию домена отскоком. Такие заказы уходят в ручной разбор.
        if email.rsplit("@", 1)[-1].lower() in {"example.com", "example.net", "example.org",
                                                "invalid", "localhost", "test"}:
            return {"ok": False, "mode": "shell", "reason": "test_email_blocked",
                    "order_id": order.order_id, "product_id": order.product_id}
        if self.out_dir:
            out_path = Path(self.out_dir) / order.order_id
        else:
            base = Path(os.environ.get("KARTA_REPORTS_DIR") or "/tmp/karta-reports")
            out_path = base / order.order_id
        cmd = [*self.command, "--email", email, "--send", "--out", str(out_path)]
        # Номер заказа передаём окружением: у скриптов выдачи он обязателен, а
        # дописывать флаги в каждую команду — значит забыть в следующей.
        env = {**os.environ, "PAY_ORDER_ID": order.order_id,
               "PAY_PRODUCT_ID": order.product_id}
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=self.timeout, env=env)
            if proc.returncode != 0:
                # Пустой stdout упавшего скрипта нельзя читать как «выдано, но без письма».
                return {"ok": False, "mode": "shell", "reason": f"delivery_failed: exit {proc.returncode}",
                        "order_id": order.order_id, "product_id": order.product_id}
            data = _json.loads(proc.stdout or "{}")
        except Exception as exc:
            return {"ok": False, "mode": "shell", "reason": f"delivery_failed: {exc.__class__.__name__}",
                    "order_id": order.order_id, "product_id": order.product_id}
        ok = bool(data.get("files")) and bool(data.get("emailed"))
        return {"ok": ok, "mode": "shell", "order_id": order.order_id,
                "product_id": order.product_id, "files": data.get("files"),
                "emailed": bool(data.get("emailed")),
                "reason": data.get("email_reason") or ("sent" if ok else "not_delivered")}


def product_hooks() -> dict[str, FulfillmentHook]:
    """Какие продукты выдаются автоматом. Остальные — руками, как раньше."""
    import os

    hooks: dict[str, FulfillmentHook] = {}
    # Каждый продукт со своей командой выдачи: одна переменная на товар, чтобы
    # включение разбора не включало заодно отчёт.
    for env_key, product in (("KARTA_REPORT_CMD", "karta-report"),
                             ("AIBIZ_REVIEW_CMD", "aibiz-review")):
        cmd = os.environ.get(env_key)
        if cmd:
            hooks[product] = ShellDelivery(
                command=cmd.split(),
                out_dir=os.environ.get("AIBIZ_ORDERS_DIR") if product == "aibiz-review" else None,
            )
    return hooks


def hook_for(order: OrderRecord | None, hooks: dict[str, FulfillmentHook] | None = None) -> FulfillmentHook:
    """Хук по продукту заказа; по умолчанию — ручная выдача."""
    hooks = hooks if hooks is not None else product_hooks()
    if order is not None and order.product_id in hooks:
        return hooks[order.product_id]
    return ManualFulfillment.from_env()


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
