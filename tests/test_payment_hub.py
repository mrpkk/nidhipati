from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs, urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from nidhipati_proof.payment_hub import (
    CreatePaymentRequest,
    InMemoryIdempotencyStore,
    PayGateCardAdapter,
    PaymentPolicy,
    PaymentStatus,
    evaluate_policy,
    verify_paygate_signature,
)


def _req(**kw):
    base = dict(
        order_id="ord-1",
        amount_fiat="9.99",
        currency="USD",
        product_id="nidhipati.verify",
        callback_url="https://example.com/cb?order_id=ord-1",
        payout_address="0x1111111111111111111111111111111111111111",
        settlement_asset="USDC",
        settlement_network="polygon",
    )
    base.update(kw)
    return CreatePaymentRequest(**base)


def test_policy_blocks_configured_country():
    policy = PaymentPolicy(blocked_country_codes=("ZZ",))
    req = _req(payer_country="ZZ")
    blocked = evaluate_policy(req, policy)
    assert blocked is not None and not blocked.ok
    assert blocked.reason == "payer_country_blocked:ZZ"


def test_policy_allows_when_not_configured_blocked():
    assert evaluate_policy(_req(payer_country="DE")) is None
    assert evaluate_policy(_req(payer_country=None)) is None


def test_policy_blocks_bad_asset():
    res = evaluate_policy(_req(settlement_asset="EUR"))
    assert res is not None and "settlement_asset" in (res.reason or "")


def test_idempotency_store():
    s = InMemoryIdempotencyStore()
    assert s.mark("evt:1") is True
    assert s.mark("evt:1") is False
    assert s.seen("evt:1") is True


def test_paygate_create_payment_mock():
    calls = []

    def http_get(url, headers, timeout):
        calls.append(url)
        body = json.dumps({
            "address_in": "enc_addr",
            "polygon_address_in": "0xpoly",
            "callback_url": "https://example.com/cb?order_id=ord-1",
            "ipn_token": "tok",
        }).encode()
        return 200, body, {}

    adapter = PayGateCardAdapter(http_get=http_get)
    res = adapter.create_payment(_req())
    assert res.ok is True
    assert res.status == PaymentStatus.PENDING
    assert res.provider_ref and res.provider_ref.address_in == "enc_addr"
    assert res.provider_ref.checkout_url and "checkout.paygate.to/pay.php" in res.provider_ref.checkout_url
    q = parse_qs(urlsplit(res.provider_ref.checkout_url).query)
    assert q["address"] == ["enc_addr"]
    assert q["amount"] == ["9.99"]
    assert calls and "wallet.php" in calls[0]


def test_paygate_normalize_paid_callback():
    adapter = PayGateCardAdapter()
    ev = adapter.normalize_callback(
        params={
            "order_id": "ord-1",
            "value_coin": "9.50",
            "coin": "polygon_usdc",
            "txid_in": "0xin",
            "txid_out": "0xout",
            "value_forwarded_coin": "9.40",
            "address_in": "0xpoly",
        },
        headers={},
        raw_url="https://example.com/cb?order_id=ord-1&txid_in=0xin",
    )
    assert ev.status == PaymentStatus.PAID
    assert ev.order_id == "ord-1"
    assert ev.txid_out == "0xout"
    assert ev.signature_verified is None


def test_paygate_signature_verify():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    base = "https://example.com/cb"
    raw_qs = "order_id=ord-1&txid_in=0xin&value_coin=9.5"
    signed = f"{base}?{raw_qs}".encode()
    sig = base64.b64encode(key.sign(signed, padding.PKCS1v15(), hashes.SHA256())).decode()
    assert verify_paygate_signature(
        registered_callback_base=base, raw_query_string=raw_qs, signature_b64=sig, public_key_pem=pub
    ) is True
    assert verify_paygate_signature(
        registered_callback_base=base, raw_query_string=raw_qs + "&tampered=1", signature_b64=sig, public_key_pem=pub
    ) is False
