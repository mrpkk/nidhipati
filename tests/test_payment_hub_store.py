from __future__ import annotations

from nidhipati_proof.payment_hub import (
    HandleResult,
    OrderRecord,
    PayGateCardAdapter,
    PaymentStatus,
    PaymentStore,
    handle_callback,
)


def test_store_order_and_idempotency():
    s = PaymentStore(":memory:")
    rec = OrderRecord("o1", "p", "10", "USD", PaymentStatus.PENDING.value)
    s.upsert_order(rec)
    got = s.get_order("o1")
    assert got and got.status == PaymentStatus.PENDING.value
    s.update_status("o1", PaymentStatus.PAID.value, txid_out="0xabc")
    assert s.get_order("o1").txid_out == "0xabc"
    assert s.mark_once("evt:1") is True
    assert s.mark_once("evt:1") is False


def test_handle_callback_idempotent():
    s = PaymentStore(":memory:")
    s.upsert_order(OrderRecord("ord-1", "nidhipati.verify", "9.99", "USD", PaymentStatus.PENDING.value))
    adapter = PayGateCardAdapter()
    params = {"order_id": "ord-1", "txid_in": "0xin", "value_coin": "9.5", "coin": "polygon_usdc"}
    r1 = handle_callback(store=s, adapter=adapter, params=params, headers={}, raw_url="https://cb?order_id=ord-1&txid_in=0xin")
    r2 = handle_callback(store=s, adapter=adapter, params=params, headers={}, raw_url="https://cb?order_id=ord-1&txid_in=0xin")
    assert r1.ok and r1.duplicate is False
    assert r2.ok and r2.duplicate is True
    assert s.get_order("ord-1").status == PaymentStatus.PAID.value
    s.close()
