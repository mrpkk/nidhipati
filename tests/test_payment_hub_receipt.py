from nidhipati_proof.payment_hub import OrderRecord, PaymentStatus, build_payment_evidence


def test_build_payment_evidence():
    order = OrderRecord("o1", "nidhipati.verify", "10", "USD", PaymentStatus.PAID.value, provider="paygate.to", txid_out="0xout")
    ev = build_payment_evidence(order=order, callback_raw={"txid_out": "0xout"}, fulfillment={"kind": "access", "ok": True})
    assert ev["kind"] == "payment_evidence"
    assert ev["order"]["order_id"] == "o1"
    assert ev["callback_raw_hash"].startswith("sha256:")
    assert ev["evidence_hash"].startswith("sha256:")
    assert ev["fulfillment"]["ok"] is True
