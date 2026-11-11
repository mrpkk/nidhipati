from nidhipati_proof.payment_hub import (
    OrderRecord, PaymentStatus, PaymentStore,
    ManualFulfillment, maybe_fulfill,
)


def test_maybe_fulfill_idempotent():
    store = PaymentStore(":memory:")
    store.upsert_order(OrderRecord("o1", "nidhipati.verify", "10", "USD", PaymentStatus.PAID.value))
    r1 = maybe_fulfill(store=store, order_id="o1", hook=ManualFulfillment())
    r2 = maybe_fulfill(store=store, order_id="o1", hook=ManualFulfillment())
    assert r1 and r1["ok"] is True
    assert r2 and r2.get("duplicate") is True
    assert store.get_order("o1").status == PaymentStatus.FULFILLED.value


def test_maybe_fulfill_skips_non_paid():
    store = PaymentStore(":memory:")
    store.upsert_order(OrderRecord("o2", "p", "10", "USD", PaymentStatus.PENDING.value))
    assert maybe_fulfill(store=store, order_id="o2") is None
    assert store.get_order("o2").status == PaymentStatus.PENDING.value
