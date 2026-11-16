"""Колбэк без подписи провайдера не делает заказ оплаченным.

Гейт: тело колбэка — недоверенный ввод. Если подписи нет, статус берётся у
провайдера по серверному токену (ipn_token из meta заказа), а не из тела.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nidhipati_proof.payment_hub.handler import handle_callback
from nidhipati_proof.payment_hub.models import (
    PaymentEvent,
    PaymentStatus,
    ProviderRef,
)
from nidhipati_proof.payment_hub.store import OrderRecord, PaymentStore


class StubAdapter:
    provider = "paygate.to"

    def __init__(self, status: PaymentStatus | None) -> None:
        self.status = status
        self.asked: list[ProviderRef] = []

    def normalize_callback(self, *, params, headers, raw_url):
        return PaymentEvent(
            provider=self.provider,
            order_id=params.get("order_id"),
            status=PaymentStatus.PAID if params.get("txid_in") else PaymentStatus.PENDING,
            signature_verified=None,
            raw=dict(params),
        )

    def check_status(self, ref: ProviderRef):
        self.asked.append(ref)
        if self.status is None:
            return None
        return PaymentEvent(provider=self.provider, order_id=None, status=self.status,
                            txid_out="0xabc", signature_verified=None, raw={})


def _store_with_order(meta: dict | None = None) -> PaymentStore:
    store = PaymentStore(":memory:")
    store.upsert_order(OrderRecord(
        order_id="o-1", product_id="agent-spend-audit", amount_fiat="500",
        currency="USD", status=PaymentStatus.PENDING.value, provider="paygate.to",
        meta=meta if meta is not None else {"ipn_token": "tok-1"},
    ))
    return store


def _callback(store, adapter):
    return handle_callback(
        store=store, adapter=adapter,
        params={"order_id": "o-1", "txid_in": "0xdead"},
        headers={}, raw_url="https://nidhipati.rta.lat/pay/callback?order_id=o-1",
    )


def test_unverified_callback_without_provider_confirmation_stays_pending():
    store = _store_with_order()
    result = _callback(store, StubAdapter(PaymentStatus.PENDING))
    assert result.ok is False
    assert result.reason == "provider_not_confirmed"
    assert store.get_order("o-1").status == PaymentStatus.PENDING.value


def test_unverified_callback_with_provider_confirmation_marks_paid():
    store = _store_with_order()
    adapter = StubAdapter(PaymentStatus.PAID)
    result = _callback(store, adapter)
    assert result.ok is True
    assert adapter.asked[0].ipn_token == "tok-1"
    assert store.get_order("o-1").status == PaymentStatus.PAID.value


def test_callback_without_order_token_is_rejected():
    store = _store_with_order(meta={})
    result = _callback(store, StubAdapter(PaymentStatus.PAID))
    assert result.ok is False
    assert result.reason == "callback_unverified_and_no_provider_token"
    assert store.get_order("o-1").status == PaymentStatus.PENDING.value
