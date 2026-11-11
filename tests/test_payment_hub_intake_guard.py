"""Почта проекта не должна стать чужим инструментом.

Заказ можно создать с любым адресом и любой ценой. Если форму заявки слать
всем подряд, то за 0.001 USDC можно рассылать письма от имени проекта
посторонним людям. Поэтому письмо уходит только по каталогу: продукт есть,
и цена совпадает с его ценой.
"""
from __future__ import annotations

import pytest

import nidhipati_proof.payment_hub.web as web
from nidhipati_proof.payment_hub import intake
from nidhipati_proof.payment_hub.base_rpc import TRANSFER_TOPIC, USDC_BASE

WALLET = "0xefCD6886f73064ea9EcbaA4741Ef1309A0885C59"
TX = "0x" + "1a" * 32
OTHER_TX = "0x" + "2b" * 32


def _topic(address: str) -> str:
    return "0x" + "0" * 24 + address[2:].lower()


def _receipt(amount: int) -> dict:
    return {
        "status": hex(1),
        "blockNumber": hex(100),
        "logs": [{
            "address": USDC_BASE,
            "topics": [TRANSFER_TOPIC, _topic("0x" + "33" * 20), _topic(WALLET)],
            "data": hex(amount),
        }],
    }


@pytest.fixture()
def hub(monkeypatch, tmp_path):
    monkeypatch.setenv("NIDHIPATI_PAYMENT_DB", str(tmp_path / "pay.db"))
    monkeypatch.setenv("NIDHIPATI_PAYOUT_ADDRESS", WALLET)
    monkeypatch.setenv("PAYMENT_HUB_NETWORK", "base")
    monkeypatch.setenv("PAYMENT_HUB_ASSET", "USDC")
    web._STORE = None
    web._STORE_PATH = None
    return web


def _install_fetch(monkeypatch, receipts: dict):
    def fetch(url: str, method: str, params: list) -> dict:
        if method == "eth_getTransactionReceipt":
            return {"result": receipts.get(params[0])}
        if method == "eth_blockNumber":
            return {"result": hex(1000)}
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("nidhipati_proof.payment_hub.base_rpc._default_fetch", fetch)


def test_catalog_order_gets_the_intake_form(hub, monkeypatch):
    _install_fetch(monkeypatch, {TX: _receipt(500_000_000)})
    hub._handle_create({"order_id": "c-1", "amount_fiat": "500",
                        "product_id": "agent-spend-audit",
                        "customer_email": "buyer@example.com"})
    status, payload, _ = hub._handle_confirm({"order_id": "c-1", "tx_hash": TX})
    assert status == 200
    assert payload["intake_email_sent"] is True
    assert payload["intake_skipped_reason"] is None


def test_unknown_product_gets_no_form(hub, monkeypatch):
    _install_fetch(monkeypatch, {TX: _receipt(1_000_000)})
    hub._handle_create({"order_id": "c-2", "amount_fiat": "1",
                        "product_id": "not-a-product",
                        "customer_email": "victim@example.com"})
    status, payload, _ = hub._handle_confirm({"order_id": "c-2", "tx_hash": TX})
    assert status == 200
    assert payload["intake_email_sent"] is False
    assert payload["intake_skipped_reason"] == "product_not_in_catalog"


def test_price_below_catalog_gets_no_form(hub, monkeypatch):
    _install_fetch(monkeypatch, {TX: _receipt(1_000_000)})
    hub._handle_create({"order_id": "c-3", "amount_fiat": "0.001",
                        "product_id": "agent-spend-audit",
                        "customer_email": "victim@example.com"})
    status, payload, _ = hub._handle_confirm({"order_id": "c-3", "tx_hash": TX})
    assert status == 200
    assert payload["intake_email_sent"] is False
    assert payload["intake_skipped_reason"] == "amount_does_not_match_catalog_price"


def test_owner_is_still_notified_for_odd_orders(hub, monkeypatch):
    """Владелец узнаёт обо всех оплатах — иначе деньги придут в никуда."""
    _install_fetch(monkeypatch, {TX: _receipt(1_000_000)})
    hub._handle_create({"order_id": "c-4", "amount_fiat": "1",
                        "product_id": "not-a-product"})
    status, payload, _ = hub._handle_confirm({"order_id": "c-4", "tx_hash": TX})
    assert status == 200
    assert payload["owner_notified"] is True
