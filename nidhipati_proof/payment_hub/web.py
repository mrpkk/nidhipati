from __future__ import annotations

import json
import os
import urllib.parse
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from .handler import handle_callback
from .fulfillment import ManualFulfillment, hook_for, maybe_fulfill
from .paygate import PayGateCardAdapter
from .direct import DirectBaseAdapter, ChainUnavailable, TransferRejected, adapter_from_env
from .checkout import PRODUCTS, checkout_page
from .intake import notify_owner, send_intake, valid_email
from .receipt import build_payment_evidence
from .store import PaymentStore, OrderRecord
from .models import CreatePaymentRequest, PaymentStatus

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


def handle_pay_get(path: str, query: Mapping[str, str],
                   headers: Mapping[str, str] | None = None
                   ) -> tuple[int, dict[str, Any], dict[str, str]] | None:
    p = path.rstrip("/")
    if p.endswith("/pay/funnel"):
        # Касса: сколько открыли страницу оплаты и сколько создали заказ.
        # Без этого «0 покупок» неотличимо от «до кассы не дошли».
        import json as _j  # не _json: так зовут HTTP-хелпер ниже
        from .checkout import FUNNEL_PATH
        try:
            data = _j.loads(FUNNEL_PATH.read_text())
        except (OSError, ValueError):
            data = {}
        rows: dict[str, dict[str, int | str]] = {}
        for key, value in data.items():
            kind, _, product = key.partition(":")
            row = rows.setdefault(product, {"views": 0, "orders": 0})
            row["views" if kind == "view" else "orders"] = int(value)
        for row in rows.values():
            v = int(row["views"])
            row["view_to_order"] = f"{int(row['orders']) / v:.3f}" if v else "—"
        return _json(200, {"products": rows,
                           "total_views": sum(int(r["views"]) for r in rows.values()),
                           "total_orders": sum(int(r["orders"]) for r in rows.values())})
    if p.endswith("/pay/health"):
        return _json(200, {
            "status": "ok",
            "service": "nidhipati-payment-hub",
            "rails": {
                "direct.base": {
                    "settlement": "USDC/Base",
                    "payout_configured": bool(os.environ.get("NIDHIPATI_PAYOUT_ADDRESS")),
                    "wiring": "create+confirm+order+evidence",
                },
                "paygate.to": {
                    "settlement": "USDC/Polygon",
                    "callback_base_configured": bool(os.environ.get("PAYGATE_CALLBACK_BASE_URL")),
                    "signature_key_configured": bool(os.environ.get("PAYGATE_CALLBACK_PUBLIC_KEY_PEM") or os.environ.get("PAYGATE_CALLBACK_PUBLIC_KEY_FILE")),
                },
            },
        })
    if p.endswith("/pay/refunds"):
        if not _admin_ok(headers or {}):
            return _json(403, {"error": "admin_token_required"})
        rows = get_store().list_refunded()
        return _json(200, {"refunds": rows, "count": len(rows),
                           "total_fiat": sum(float(r["amount"] or 0) for r in rows)})
    if "/pay/order/" in p:
        order_id = p.rsplit("/pay/order/", 1)[-1].split("/", 1)[0]
        store = get_store()
        order = store.get_order(order_id)
        if not order:
            return _json(404, {"error": "not_found", "order_id": order_id})
        evidence = build_payment_evidence(order=order)
        return _json(200, {"order": order.__dict__, "evidence": evidence})
    if p.endswith("/pay/config"):
        # Non-secret config view for ops/debug
        return _json(200, {
            "rails": ["direct.base", "paygate.to"],
            "settlement": {"direct.base": "USDC/Base", "paygate.to": "USDC/Polygon"},
            "callback_base_configured": bool(os.environ.get("PAYGATE_CALLBACK_BASE_URL")),
            "signature_key_configured": bool(os.environ.get("PAYGATE_CALLBACK_PUBLIC_KEY_PEM") or os.environ.get("PAYGATE_CALLBACK_PUBLIC_KEY_FILE")),
            "payout_configured": bool(os.environ.get("NIDHIPATI_PAYOUT_ADDRESS")),
            "network": os.environ.get("PAYMENT_HUB_NETWORK", "base"),
            "asset": os.environ.get("PAYMENT_HUB_ASSET", "USDC"),
            "fulfillment_note_configured": bool(os.environ.get("NIDHIPATI_FULFILLMENT_NOTE")),
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
        return handle_pay_get(path, qs, headers)

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
        if path.rstrip("/").endswith("/pay/refund"):
            if not _admin_ok(headers):
                return _json(403, {"error": "admin_token_required"})
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
            except Exception:
                return _json(400, {"error": "bad_json"})
            return _handle_refund(payload if isinstance(payload, dict) else {})
        if path.rstrip("/").endswith("/pay/create"):
            payload: dict[str, Any] = {}
            if body:
                try:
                    data = json.loads(body.decode("utf-8"))
                    if isinstance(data, dict):
                        payload = data
                except Exception:
                    return _json(400, {"error": "invalid_json"})
            return _handle_create(payload)
        if path.rstrip("/").endswith("/pay/confirm"):
            payload: dict[str, Any] = {}
            if body:
                try:
                    data = json.loads(body.decode("utf-8"))
                    if isinstance(data, dict):
                        payload = data
                except Exception:
                    return _json(400, {"error": "invalid_json"})
            return _handle_confirm(payload)
    return _json(405, {"error": "method_not_allowed", "path": path})


def _handle_callback(parsed: urllib.parse.SplitResult, params: Mapping[str, str], headers: Mapping[str, str]):
    store = get_store()
    adapter = get_adapter()
    raw_url = urllib.parse.urlunsplit(parsed)
    result = handle_callback(store=store, adapter=adapter, params=params, headers={k.lower(): v for k, v in headers.items()}, raw_url=raw_url)
    fulfillment = None
    if result.ok and result.order_id and result.status in {"paid", "settled"}:
        fulfillment = maybe_fulfill(store=store, order_id=result.order_id,
                                    hook=hook_for(store.get_order(result.order_id)),
                                    event=dict(params))
    return _json(200 if result.ok else 400, {
        "ok": result.ok,
        "duplicate": result.duplicate,
        "order_id": result.order_id,
        "status": result.status,
        "reason": result.reason,
        "fulfillment": fulfillment,
    })


def _admin_ok(headers: Mapping[str, str]) -> bool:
    """Владельческая операция: сравнение токена в постоянном времени.

    Возврат — не клиентская кнопка: без токена из `~/.config/nidhipati/payment.env`
    ручка отвечает 403, а не «попробуйте ещё раз».
    """
    import hmac

    expected = (os.environ.get("NIDHIPATI_ADMIN_TOKEN") or "").strip()
    if not expected:
        return False
    got = (headers.get("X-Nidhipati-Admin") or headers.get("x-nidhipati-admin") or "").strip()
    return bool(got) and hmac.compare_digest(got, expected)


def _handle_refund(payload: Mapping[str, Any]) -> tuple[int, dict[str, Any], dict[str, str]]:
    """Отметить заказ возвращённым: статус, причина, хеш возврата.

    Деньги возвращает человек (карта — через провайдера, USDC — переводом), здесь
    фиксируется факт и доказательство: без `tx_hash`/`refund_ref` возврат не
    считается закрытым, потому что проверить его нечем.
    """
    order_id = str(payload.get("order_id") or "").strip()
    if not order_id:
        return _json(400, {"error": "order_id_required"})
    store = get_store()
    order = store.get_order(order_id)
    if not order:
        return _json(404, {"error": "not_found", "order_id": order_id})
    if order.status == "refunded":
        return _json(200, {"ok": True, "duplicate": True, "order": order.__dict__})
    reason = str(payload.get("reason") or "").strip()[:200]
    if not reason:
        return _json(400, {"error": "reason_required",
                           "hint": "одна строка: что не доставлено и какой срок нарушен"})
    tx_hash = str(payload.get("tx_hash") or "").strip()
    refund_ref = str(payload.get("refund_ref") or "").strip()  # возврат карты у провайдера
    if not tx_hash and not refund_ref:
        return _json(400, {"error": "evidence_required",
                           "hint": "нужен tx_hash (USDC) или refund_ref (карта): без него возврат не проверить"})
    meta = dict(order.meta or {})
    meta.update({"refund_reason": reason, "refunded_at": __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).isoformat(timespec="seconds")})
    if tx_hash:
        meta["refund_tx_hash"] = tx_hash
    if refund_ref:
        meta["refund_ref"] = refund_ref
    store.update_status(order_id, "refunded", meta=meta)
    store.record_event(event_key=f"refund:{order_id}", order_id=order_id,
                       provider=order.provider or "manual", status="refunded",
                       raw={"reason": reason, "tx_hash": tx_hash, "refund_ref": refund_ref})
    fresh = store.get_order(order_id)
    # Покупатель должен узнать о возврате из письма, а не из выписки. Ошибку
    # отправки не прячем: она попадёт в ответ владельцу.
    email_note = "skipped"
    customer = str((fresh.meta or {}).get("customer_email") or "") if fresh else ""
    if customer:
        try:
            from .intake import send_refund_email

            email_note = send_refund_email(customer, fresh.__dict__ if fresh else {},
                                           reason, tx_hash or refund_ref) or "sent"
        except Exception as exc:  # noqa: BLE001
            email_note = f"error:{type(exc).__name__}"
    return _json(200, {"ok": True, "order": fresh.__dict__ if fresh else None,
                       "refund_email": email_note})


def _rail_of(payload: Mapping[str, Any]) -> str:
    """Какой рельс выбран: прямой (USDC/Base) или карточный (PayGate.to).

    По умолчанию — прямой: он работает без KYC и без регистрации у провайдера.
    Карточный включается явно (`rail: "paygate.to"`), когда владелец примет его
    ToS.
    """
    rail = str(payload.get("rail") or os.environ.get("NIDHIPATI_PAYMENT_RAIL") or "direct").strip().lower()
    if rail in ("direct", "direct.base", "usdc", "usdc/base", "base"):
        return "direct.base"
    return "paygate.to"


def _atoms_for(amount_fiat: str) -> int:
    """Цена в долларах → атомы USDC (1:1). Ошибка разбора — честный отказ."""
    try:
        return int((Decimal(amount_fiat) * 1_000_000).to_integral_value())
    except (InvalidOperation, ValueError, TypeError):
        return -1


def _handle_create_direct(payload: Mapping[str, Any], order_id: str, amount_fiat: str,
                          currency: str, product_id: str):
    """Прямой рельс: покупатель сам шлёт USDC на адрес и присылает хеш.

    Витрины у этого рельса нет — вместо неё инструкция: адрес, сумма, сеть и
    адрес подтверждения. Ключ выдаётся в тот же ответ, что и квитанция, поэтому
    цепочка «заказ → оплата → подтверждение → выдача» не разорвана.
    """
    store = get_store()
    existing = store.get_order(order_id)
    if existing:
        return _json(200, {"ok": True, "duplicate": True, "order": existing.__dict__})
    adapter = adapter_from_env()
    if not adapter.payout_address:
        return _json(400, {
            "error": "payout_not_configured",
            "hint": "Set NIDHIPATI_PAYOUT_ADDRESS in /home/iamthat/.config/nidhipati/payment.env",
        })
    atoms = _atoms_for(amount_fiat)
    if atoms <= 0:
        return _json(400, {"error": "amount_fiat_must_be_a_number", "amount_fiat": amount_fiat})
    email = str(payload.get("customer_email") or "").strip()
    if email and not valid_email(email):
        return _json(400, {"error": "customer_email_is_not_valid", "customer_email": email})
    req = CreatePaymentRequest(
        order_id=order_id,
        amount_fiat=amount_fiat,
        currency=currency,
        product_id=product_id,
        callback_url="",  # у прямого рельса колбэка нет: оплату подтверждает покупатель хешем
        payout_address=adapter.payout_address,
        customer_email=email or None,
        settlement_asset=adapter.asset,
        settlement_network=adapter.network,
    )
    result = adapter.create_payment(req)
    if not result.ok or not result.provider_ref:
        rec = OrderRecord(order_id, product_id, amount_fiat, currency, PaymentStatus.FAILED.value,
                          provider=adapter.provider, meta={"reason": result.reason})
        store.upsert_order(rec)
        return _json(400, {"ok": False, "error": result.reason, "order": rec.__dict__})
    rec = OrderRecord(
        order_id=order_id,
        product_id=product_id,
        amount_fiat=amount_fiat,
        currency=currency,
        status=PaymentStatus.PENDING.value,
        provider=adapter.provider,
        checkout_url=None,
        provider_ref=adapter.payout_address,
        meta={"asset": adapter.asset, "network": adapter.network,
              "min_atoms": atoms, "amount_usdc": f"{atoms / 1_000_000:.6f}",
              "customer_email": email or None},
    )
    store.upsert_order(rec)
    try:
        from .checkout import funnel_bump
        funnel_bump("order", product_id)
    except Exception:
        pass
    return _json(200, {
        "ok": True,
        "order": rec.__dict__,
        "payment": {
            "asset": adapter.asset,
            "network": adapter.network,
            "address": adapter.payout_address,
            "amount": f"{atoms / 1_000_000:.6f}",
            "how": (f"Send {atoms / 1_000_000:.6f} {adapter.asset} on {adapter.network} to "
                    f"{adapter.payout_address}, then POST the transaction hash to /pay/confirm."),
        },
        "confirm_endpoint": "/pay/confirm",
        "order_endpoint": f"/pay/order/{order_id}",
    })


def _handle_confirm(payload: Mapping[str, Any]):
    """Подтверждение оплаты по хешу: сверка в сети, идемпотентная выдача."""
    order_id = str(payload.get("order_id") or "").strip()
    tx_hash = str(payload.get("tx_hash") or "").strip()
    if not order_id or not tx_hash:
        return _json(400, {"error": "order_id_and_tx_hash_required"})
    store = get_store()
    order = store.get_order(order_id)
    if not order:
        return _json(404, {"error": "not_found", "order_id": order_id})
    adapter = adapter_from_env()
    min_atoms = int((order.meta or {}).get("min_atoms") or 0)
    if min_atoms <= 0:
        min_atoms = _atoms_for(order.amount_fiat)
    try:
        event = adapter.confirm(tx_hash, order_id=order_id, min_atoms=min_atoms)
    except TransferRejected as exc:
        return _json(402, {"error": str(exc), "order_id": order_id,
                           "required_usdc": f"{min_atoms / 1_000_000:.6f}"})
    except ChainUnavailable as exc:
        return _json(503, {"error": f"could not check the chain: {exc}"})
    facts = dict(event.raw)
    # Один перевод — одна выдача: повторный confirm того же хеша не выдаёт снова.
    if not store.mark_once(f"tx:{event.txid_in}"):
        return _json(409, {"error": "this transaction was already used",
                           "order_id": order_id, "tx_hash": event.txid_in})
    store.update_status(order_id, PaymentStatus.PAID.value,
                         provider=adapter.provider, provider_ref=adapter.payout_address,
                         txid_in=event.txid_in, signature_verified=None)
    fulfillment = maybe_fulfill(store=store, order_id=order_id,
                                hook=hook_for(store.get_order(order_id)), event=facts)
    fresh = store.get_order(order_id)
    evidence = build_payment_evidence(order=fresh, provider_event=facts, fulfillment=fulfillment)
    # Письма: покупателю — форма заявки, владельцу — уведомление. Ошибка письма
    # не отменяет оплату: деньги уже в сети, заказ записан. Но сказать об этом
    # нужно честно, иначе покупатель будет ждать письмо, которого не будет.
    #
    # Форму заявки шлём только по каталогу: продукт есть и цена совпадает.
    # Иначе любой создал бы заказ на 0.001 USDC с чужим адресом и отправлял
    # письма от имени проекта — почта проекта стала бы чужим инструментом.
    email = ""
    intake_skip = None
    if fresh:
        catalog = PRODUCTS.get(fresh.product_id)
        if not catalog:
            intake_skip = "product_not_in_catalog"
        elif _atoms_for(catalog["price_usd"]) != int((fresh.meta or {}).get("min_atoms") or 0):
            intake_skip = "amount_does_not_match_catalog_price"
        else:
            email = str((fresh.meta or {}).get("customer_email") or "")
    intake_error = ""
    if email:
        intake_error = send_intake(email, order=fresh.__dict__ if fresh else {}, evidence=evidence)
    owner_error = notify_owner(order=fresh.__dict__ if fresh else {}, evidence=evidence)
    return _json(200, {
        "ok": True,
        "paid": True,
        "order_id": order_id,
        "status": fresh.status if fresh else None,
        "amount_usdc": event.amount,
        "payer": facts.get("payer"),
        "tx_hash": event.txid_in,
        "block": facts.get("block"),
        "confirmations": facts.get("confirmations"),
        "fulfillment": fulfillment,
        "intake_email_sent": bool(email) and not intake_error,
        "intake_email_error": intake_error or None,
        "intake_skipped_reason": intake_skip,
        "owner_notified": not owner_error,
        "evidence": evidence,
    })


def _handle_create(payload: dict[str, Any]):
    order_id = str(payload.get("order_id") or "").strip()
    amount_fiat = str(payload.get("amount_fiat") or "").strip()
    currency = str(payload.get("currency") or "USD").strip().upper()
    product_id = str(payload.get("product_id") or "nidhipati").strip()
    customer_email = payload.get("customer_email")
    provider_name = payload.get("provider_name")
    if not order_id or not amount_fiat:
        return _json(400, {"error": "order_id_and_amount_fiat_required"})
    if _rail_of(payload) == "direct.base":
        return _handle_create_direct(payload, order_id, amount_fiat, currency, product_id)
    store = get_store()
    existing = store.get_order(order_id)
    if existing:
        return _json(200, {"ok": True, "duplicate": True, "order": existing.__dict__})
    payout = (os.environ.get("NIDHIPATI_PAYOUT_ADDRESS") or "").strip()
    if not payout:
        return _json(400, {"error": "payout_not_configured", "hint": "Set NIDHIPATI_PAYOUT_ADDRESS in /home/iamthat/.config/nidhipati/payment.env"})
    callback_base = (os.environ.get("PAYGATE_CALLBACK_BASE_URL") or "https://nidhipati.rta.lat/pay/callback").strip()
    cb = callback_base
    if "order_id=" not in cb:
        sep = "&" if "?" in cb else "?"
        cb = f"{cb}{sep}order_id={urllib.parse.quote(order_id)}"
    req = CreatePaymentRequest(
        order_id=order_id,
        amount_fiat=amount_fiat,
        currency=currency,
        product_id=product_id,
        callback_url=cb,
        payout_address=payout,
        customer_email=str(customer_email) if customer_email else None,
        provider_name=str(provider_name) if provider_name else None,
        settlement_asset="USDC",
        settlement_network="polygon",
    )
    adapter = get_adapter()
    result = adapter.create_payment(req)
    if not result.ok or not result.provider_ref:
        rec = OrderRecord(order_id, product_id, amount_fiat, currency, PaymentStatus.FAILED.value, provider=adapter.provider, meta={"reason": result.reason})
        store.upsert_order(rec)
        return _json(400, {"ok": False, "error": result.reason, "order": rec.__dict__})
    rec = OrderRecord(
        order_id=order_id,
        product_id=product_id,
        amount_fiat=amount_fiat,
        currency=currency,
        status=PaymentStatus.PENDING.value,
        provider=adapter.provider,
        checkout_url=result.provider_ref.checkout_url,
        provider_ref=result.provider_ref.address_in,
        # 20.11.2026: карточный путь собирал email, но не сохранял его в заказе —
        # автоматическая выдача (KARTA/AIBiz) не могла написать покупателю и
        # уходила в manual_review с «customer_email_missing».
        meta={"ipn_token": result.provider_ref.ipn_token,
              "polygon_address_in": result.provider_ref.polygon_address_in,
              "customer_email": str(customer_email) if customer_email else None},
    )
    store.upsert_order(rec)
    return _json(200, {"ok": True, "order": rec.__dict__, "checkout_url": rec.checkout_url})
