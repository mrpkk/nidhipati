"""Прямой рельс оплаты: USDC в Base, сверка по хешу в сети.

Проверяется то, что не проверяется подменённой нодой: ошибки разбора,
неверный получатель, недоплата, повторный хеш и «сеть не ответила» — это
разные причины, и клиенту нужны разные ответы.
"""
from __future__ import annotations

import json

import pytest

from nidhipati_proof.payment_hub import (
    ChainUnavailable,
    DirectBaseAdapter,
    PaymentStatus,
    TransferRejected,
)
from nidhipati_proof.payment_hub.base_rpc import TRANSFER_TOPIC, USDC_BASE

WALLET = "0xefCD6886f73064ea9EcbaA4741Ef1309A0885C59"
PAYER = "0x802b7e69bD4176DBc4a72b19465946Be5DC86E4B"
OTHER = "0x" + "22" * 20
TX = "0x" + "ab" * 32


def _topic(address: str) -> str:
    return "0x" + "0" * 24 + address[2:].lower()


def _receipt(*, to: str = WALLET, amount: int = 5_000_000, status: int = 1,
             block: int = 100, asset: str = USDC_BASE) -> dict:
    return {
        "status": hex(status),
        "blockNumber": hex(block),
        "logs": [{
            "address": asset,
            "topics": [TRANSFER_TOPIC, _topic(PAYER), _topic(to)],
            "data": hex(amount),
        }],
    }


_MISSING = object()


def _fake_fetch(receipt=_MISSING, *, head: int = 1000, error: bool = False):
    def fetch(url: str, method: str, params: list) -> dict:
        if error:
            raise RuntimeError("node is down")
        if method == "eth_getTransactionReceipt":
            return {"result": _receipt() if receipt is _MISSING else receipt}
        if method == "eth_blockNumber":
            return {"result": hex(head)}
        raise AssertionError(f"unexpected method {method}")
    return fetch


def _adapter(fetch, **kw) -> DirectBaseAdapter:
    return DirectBaseAdapter(payout_address=WALLET, fetch=fetch, **kw)


def test_valid_transfer_is_confirmed():
    adapter = _adapter(_fake_fetch())
    event = adapter.confirm(TX, order_id="o1", min_atoms=5_000_000)
    assert event.status is PaymentStatus.PAID
    assert event.txid_in == TX
    assert event.amount == "5.000000"
    assert event.raw["payer"] == PAYER.lower()
    assert event.raw["confirmations"] == 901


def test_wrong_recipient_is_rejected():
    # Кошелёк адаптера смотрит на свой адрес: перевод в чужой — не оплата.
    adapter = DirectBaseAdapter(payout_address=OTHER, fetch=_fake_fetch())
    with pytest.raises(TransferRejected, match="no USDC transfer"):
        adapter.confirm(TX, order_id="o1", min_atoms=1)


def test_underpayment_is_rejected():
    adapter = _adapter(_fake_fetch())
    with pytest.raises(TransferRejected, match="required"):
        adapter.confirm(TX, order_id="o1", min_atoms=9_000_000)


def test_failed_transaction_is_rejected():
    adapter = _adapter(_fake_fetch(_receipt(status=0)))
    with pytest.raises(TransferRejected, match="failed on-chain"):
        adapter.confirm(TX, order_id="o1", min_atoms=1)


def test_unconfirmed_transaction_is_rejected():
    adapter = _adapter(_fake_fetch(head=100), confirmations=2)
    with pytest.raises(TransferRejected, match="confirmations"):
        adapter.confirm(TX, order_id="o1", min_atoms=1)


def test_malformed_hash_is_rejected_before_any_rpc():
    calls = []

    def fetch(url: str, method: str, params: list) -> dict:
        calls.append(method)
        return {"result": None}

    adapter = _adapter(fetch)
    with pytest.raises(TransferRejected, match="tx hash"):
        adapter.confirm("not-a-hash", order_id="o1", min_atoms=1)
    assert calls == []


def test_dead_network_is_not_reported_as_unpaid():
    adapter = _adapter(_fake_fetch(error=True))
    with pytest.raises(ChainUnavailable):
        adapter.confirm(TX, order_id="o1", min_atoms=1)


def test_missing_receipt_is_rejected():
    adapter = _adapter(_fake_fetch(receipt=None))
    with pytest.raises(TransferRejected, match="not found"):
        adapter.confirm(TX, order_id="o1", min_atoms=1)


def test_create_payment_refuses_another_network():
    from nidhipati_proof.payment_hub import CreatePaymentRequest

    adapter = _adapter(_fake_fetch())
    req = CreatePaymentRequest(
        order_id="o1", amount_fiat="10", currency="USD", product_id="p",
        callback_url="", payout_address=WALLET,
        settlement_asset="USDC", settlement_network="polygon",
    )
    result = adapter.create_payment(req)
    assert not result.ok
    assert "base" in (result.reason or "")


def test_create_payment_returns_payout_instructions():
    from nidhipati_proof.payment_hub import CreatePaymentRequest

    adapter = _adapter(_fake_fetch())
    req = CreatePaymentRequest(
        order_id="o1", amount_fiat="10", currency="USD", product_id="p",
        callback_url="", payout_address=WALLET,
        settlement_asset="USDC", settlement_network="base",
    )
    result = adapter.create_payment(req)
    assert result.ok
    assert result.provider_ref.address_in == WALLET
    assert result.provider_ref.raw["network"] == "base"
    assert result.provider_ref.checkout_url is None


def test_json_body_is_not_accepted_as_signed_proof():
    """Подпись провайдера у прямого рельса нет — и не притворяется, что есть."""
    adapter = _adapter(_fake_fetch())
    assert adapter.verify_callback(headers={}, raw_url="https://x/pay/confirm") is None
