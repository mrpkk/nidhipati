import json
import os

import nidhipati_proof.payment_hub.web as web
from nidhipati_proof.payment_hub import PayGateCardAdapter, PaymentStore


class _FakeResp:
    def __init__(self, code, payload):
        self.code = code
        self._payload = payload
        self.headers = {}
    def read(self):
        return json.dumps(self._payload).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False


def fake_get(url, headers=None, timeout=20.0):
    return 200, json.dumps({"address_in": "addr_in_1", "polygon_address_in": "0xpoly", "ipn_token": "tok"}).encode(), {}


def test_create_order_happy_path(monkeypatch, tmp_path):
    db = tmp_path / "pay.db"
    monkeypatch.setenv("NIDHIPATI_PAYMENT_DB", str(db))
    monkeypatch.setenv("NIDHIPATI_PAYOUT_ADDRESS", "0x1111111111111111111111111111111111111111")
    monkeypatch.setenv("PAYGATE_CALLBACK_BASE_URL", "https://nidhipati.rta.lat/pay/callback")
    # reset store cache
    web._STORE = None; web._STORE_PATH = None
    monkeypatch.setattr(web, "get_adapter", lambda: PayGateCardAdapter(http_get=fake_get))
    # Карточный рельс выбирается явно: по умолчанию хаб берёт прямой (USDC/Base).
    status, payload, _ = web._handle_create({"order_id": "o100", "amount_fiat": "10", "currency": "USD", "product_id": "nidhipati.verify", "rail": "paygate.to"})
    assert status == 200
    assert payload["ok"] is True
    assert "checkout_url" in payload and payload["checkout_url"]
    # duplicate
    status2, payload2, _ = web._handle_create({"order_id": "o100", "amount_fiat": "10", "currency": "USD", "product_id": "nidhipati.verify"})
    assert payload2.get("duplicate") is True


def test_create_requires_payout(monkeypatch, tmp_path):
    monkeypatch.setenv("NIDHIPATI_PAYMENT_DB", str(tmp_path / "pay.db"))
    monkeypatch.delenv("NIDHIPATI_PAYOUT_ADDRESS", raising=False)
    web._STORE = None; web._STORE_PATH = None
    status, payload, _ = web._handle_create({"order_id": "o101", "amount_fiat": "10", "currency": "USD", "product_id": "p"})
    assert status == 400
    assert payload["error"] == "payout_not_configured"
