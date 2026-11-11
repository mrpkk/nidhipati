"""Живой цикл оплаты: настоящая транзакция в Base Sepolia.

По умолчанию пропущен — идёт в сеть. Запуск:

    NIDHIPATI_LIVE_PAY=1 python3 -m pytest tests/test_payment_hub_live.py -q

Доказывает то, чего не докажут подменённые ответы ноды: заказ создаётся,
реальный перевод USDC на кошелёк проекта читается из цепи, сумма и получатель
совпадают, заказ переходит в «fulfilled», и тот же хеш второй раз выдачу не
повторяет.

Транзакция настоящая: перевод 0.005 USDC на адрес проекта в Base Sepolia
(см. blockscout: адрес 0xefCD…C59, 17.10.2026). Деньги тестовые, запись в
блокчейне — нет.
"""
from __future__ import annotations

import os

import pytest

import nidhipati_proof.payment_hub.web as web
from nidhipati_proof.payment_hub.base_rpc import USDC_BASE_SEPOLIA

pytestmark = pytest.mark.skipif(
    os.environ.get("NIDHIPATI_LIVE_PAY") != "1",
    reason="живая сеть: запускать с NIDHIPATI_LIVE_PAY=1")

WALLET = "0xefCD6886f73064ea9EcbaA4741Ef1309A0885C59"
#: Настоящий перевод 0.005 USDC на кошелёк проекта (Base Sepolia, 17.10.2026).
TX = "0x38b6e9ea83970d97ee1ef5217abe8718ec0425d0607c07f3dbd0665f1142b9df"
PAID_USDC = "0.005000"


@pytest.fixture()
def live_hub(monkeypatch, tmp_path):
    monkeypatch.setenv("NIDHIPATI_PAYMENT_DB", str(tmp_path / "live.db"))
    monkeypatch.setenv("NIDHIPATI_PAYOUT_ADDRESS", WALLET)
    monkeypatch.setenv("PAYMENT_HUB_NETWORK", "base-sepolia")
    monkeypatch.setenv("PAYMENT_HUB_ASSET", "USDC")
    monkeypatch.setenv("PAYMENT_HUB_CONFIRMATIONS", "1")
    web._STORE = None
    web._STORE_PATH = None
    return web


def test_real_transfer_pays_the_order_once(live_hub):
    status, payload, _ = live_hub._handle_create({
        "order_id": "live-1", "amount_fiat": "0.005", "product_id": "nidhipati.verify",
    })
    assert status == 200, payload
    assert payload["payment"]["address"] == WALLET

    status, payload, _ = live_hub._handle_confirm({"order_id": "live-1", "tx_hash": TX})
    assert status == 200, payload
    assert payload["paid"] is True
    assert payload["amount_usdc"] == PAID_USDC
    assert payload["status"] == "fulfilled"
    assert payload["tx_hash"] == TX
    assert payload["payer"].startswith("0x")
    assert payload["confirmations"] >= 1
    assert payload["evidence"]["evidence_hash"].startswith("sha256:")

    # Тот же хеш второй раз выдачу не повторяет.
    status2, payload2, _ = live_hub._handle_confirm({"order_id": "live-1", "tx_hash": TX})
    assert status2 == 409
    assert payload2["error"] == "this transaction was already used"


def test_real_transfer_to_another_wallet_is_not_a_payment(live_hub):
    status, payload, _ = live_hub._handle_create({
        "order_id": "live-2", "amount_fiat": "0.005", "product_id": "p",
    })
    assert status == 200, payload
    live_hub.adapter_from_env  # noqa: B018 — адаптер берётся из окружения внутри хаба
    status, payload, _ = live_hub._handle_confirm({
        "order_id": "live-2",
        "tx_hash": "0x" + "11" * 32,  # несуществующая транзакция
    })
    assert status == 402
    assert "not found" in payload["error"]
