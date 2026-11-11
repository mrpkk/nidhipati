"""Веб-слой прямого рельса: создание заказа, подтверждение, идемпотентность.

Проверяется цепочка, которую увидит покупатель: заказ → оплата → подтверждение
→ выдача. И главное — что повторное подтверждение не выдаёт второй раз.
"""
from __future__ import annotations

import pytest

import nidhipati_proof.payment_hub.web as web
from nidhipati_proof.payment_hub.base_rpc import TRANSFER_TOPIC, USDC_BASE

WALLET = "0xefCD6886f73064ea9EcbaA4741Ef1309A0885C59"
PAYER = "0x802b7e69bD4176DBc4a72b19465946Be5DC86E4B"
TX = "0x" + "cd" * 32
OTHER_TX = "0x" + "ef" * 32


def _topic(address: str) -> str:
    return "0x" + "0" * 24 + address[2:].lower()


def _receipt(*, to: str = WALLET, amount: int = 5_000_000) -> dict:
    return {
        "status": hex(1),
        "blockNumber": hex(100),
        "logs": [{
            "address": USDC_BASE,
            "topics": [TRANSFER_TOPIC, _topic(PAYER), _topic(to)],
            "data": hex(amount),
        }],
    }


@pytest.fixture()
def hub(monkeypatch, tmp_path):
    monkeypatch.setenv("NIDHIPATI_PAYMENT_DB", str(tmp_path / "pay.db"))
    monkeypatch.setenv("NIDHIPATI_PAYOUT_ADDRESS", WALLET)
    monkeypatch.setenv("PAYMENT_HUB_NETWORK", "base")
    monkeypatch.setenv("PAYMENT_HUB_ASSET", "USDC")
    monkeypatch.setenv("NIDHIPATI_FULFILLMENT_NOTE", "test_fulfillment")
    web._STORE = None
    web._STORE_PATH = None
    return web


def _install_fetch(monkeypatch, receipts: dict | None = None, *, head: int = 1000):
    receipts = receipts or {}

    def fetch(url: str, method: str, params: list) -> dict:
        if method == "eth_getTransactionReceipt":
            tx = params[0]
            return {"result": receipts.get(tx)}
        if method == "eth_blockNumber":
            return {"result": hex(head)}
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("nidhipati_proof.payment_hub.base_rpc._default_fetch", fetch)


def test_create_direct_order_returns_payment_instructions(hub, monkeypatch):
    _install_fetch(monkeypatch)
    status, payload, _ = hub._handle_create({
        "order_id": "o-1", "amount_fiat": "5", "currency": "USD", "product_id": "nidhipati.verify",
    })
    assert status == 200
    assert payload["ok"] is True
    pay = payload["payment"]
    assert pay["address"] == WALLET
    assert pay["amount"] == "5.000000"
    assert pay["network"] == "base"
    assert payload["order"]["status"] == "pending"
    assert payload["confirm_endpoint"] == "/pay/confirm"


def test_create_requires_payout_address(hub, monkeypatch):
    monkeypatch.delenv("NIDHIPATI_PAYOUT_ADDRESS", raising=False)
    status, payload, _ = hub._handle_create({"order_id": "o-2", "amount_fiat": "5"})
    assert status == 400
    assert payload["error"] == "payout_not_configured"


def test_create_rejects_non_numeric_amount(hub, monkeypatch):
    _install_fetch(monkeypatch)
    status, payload, _ = hub._handle_create({"order_id": "o-3", "amount_fiat": "many"})
    assert status == 400
    assert payload["error"] == "amount_fiat_must_be_a_number"


def test_confirm_marks_order_paid_and_fulfils_once(hub, monkeypatch):
    _install_fetch(monkeypatch, {TX: _receipt()})
    hub._handle_create({"order_id": "o-4", "amount_fiat": "5", "product_id": "p"})
    status, payload, _ = hub._handle_confirm({"order_id": "o-4", "tx_hash": TX})
    assert status == 200
    assert payload["paid"] is True
    assert payload["amount_usdc"] == "5.000000"
    assert payload["status"] == "fulfilled"
    assert payload["fulfillment"]["note"] == "test_fulfillment"
    assert payload["evidence"]["evidence_hash"].startswith("sha256:")
    assert payload["evidence"]["order"]["txid_in"] == TX

    # Повторное подтверждение того же хеша — не вторая выдача.
    status2, payload2, _ = hub._handle_confirm({"order_id": "o-4", "tx_hash": TX})
    assert status2 == 409
    assert payload2["error"] == "this transaction was already used"


def test_confirm_rejects_underpayment(hub, monkeypatch):
    _install_fetch(monkeypatch, {TX: _receipt(amount=1_000_000)})
    hub._handle_create({"order_id": "o-5", "amount_fiat": "5", "product_id": "p"})
    status, payload, _ = hub._handle_confirm({"order_id": "o-5", "tx_hash": TX})
    assert status == 402
    assert "required" in payload["error"]


def test_confirm_reports_unknown_order(hub, monkeypatch):
    _install_fetch(monkeypatch, {TX: _receipt()})
    status, payload, _ = hub._handle_confirm({"order_id": "nope", "tx_hash": TX})
    assert status == 404
    assert payload["error"] == "not_found"


def test_confirm_requires_tx_hash(hub):
    status, payload, _ = hub._handle_confirm({"order_id": "o-6"})
    assert status == 400
    assert payload["error"] == "order_id_and_tx_hash_required"


def test_same_tx_cannot_pay_two_orders(hub, monkeypatch):
    _install_fetch(monkeypatch, {TX: _receipt()})
    hub._handle_create({"order_id": "o-7", "amount_fiat": "5", "product_id": "p"})
    hub._handle_create({"order_id": "o-8", "amount_fiat": "5", "product_id": "p"})
    status, payload, _ = hub._handle_confirm({"order_id": "o-7", "tx_hash": TX})
    assert status == 200
    status2, payload2, _ = hub._handle_confirm({"order_id": "o-8", "tx_hash": TX})
    assert status2 == 409


def test_config_reports_both_rails(hub):
    status, payload, _ = web.handle_pay_get("/pay/config", {})
    assert status == 200
    assert "direct.base" in payload["rails"]
    assert payload["settlement"]["direct.base"] == "USDC/Base"
    assert payload["payout_configured"] is True
