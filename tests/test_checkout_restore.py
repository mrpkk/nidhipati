"""Страница оплаты должна переживать перезагрузку вкладки.

21.11.2026: `orderId` жил только в памяти — человек отправлял USDC, обновлял
страницу и не мог подтвердить оплату: `/pay/confirm` уходил с `order_id: null`.
Деньги списаны, доступа нет. Здесь три вещи: номер заказа сохраняется, адрес с
суммой восстанавливаются с сервера, и сервер действительно отдаёт эти поля.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def page_html() -> str:
    import sys
    sys.path.insert(0, str(ROOT))
    from nidhipati_proof.payment_hub.checkout import checkout_page

    page = checkout_page("crypto-mcp-month")
    assert page is not None
    return page[0]


def test_order_id_survives_a_reload():
    html = page_html()
    assert "localStorage.setItem(STORE_KEY, orderId)" in html
    assert "localStorage.getItem(STORE_KEY)" in html
    assert "nidhipati.order." in html


def test_address_and_amount_are_restored_from_the_server():
    html = page_html()
    assert 'fetch("/pay/order/"' in html
    assert "order.provider_ref" in html
    assert "meta.amount_usdc" in html


def test_page_still_works_without_local_storage():
    """Приватный режим: без localStorage страница обязана работать как раньше."""
    html = page_html()
    assert "catch (e)" in html
    assert 'document.getElementById("mk").onclick' in html


@pytest.fixture()
def api(tmp_path, monkeypatch):
    """Живой HTTP-сервер хаба на временной базе: проверяем форму ответа заказа."""
    import sys
    sys.path.insert(0, str(ROOT))
    from nidhipati_proof.payment_hub import web as payweb

    monkeypatch.setenv("NIDHIPATI_PAYMENT_DB", str(tmp_path / "pay.db"))
    monkeypatch.setenv("NIDHIPATI_PAYOUT_ADDRESS", "0x" + "ab" * 20)
    payweb._STORE = None  # type: ignore[attr-defined]

    class Handler:
        pass

    import json

    def call(method: str, url: str, payload: dict | None = None):
        body = json.dumps(payload).encode() if payload is not None else None
        return payweb.handle_pay_request(method, url, {"Content-Type": "application/json"}, body)

    code, order, _ = call("POST", "/pay/create", {
        "order_id": "restore-1", "amount_fiat": "19", "currency": "USD",
        "product_id": "crypto-mcp-month", "customer_email": "buyer@example.com"})
    assert code == 200, order
    return call


def test_order_endpoint_returns_what_the_page_restores(api):
    code, body, _ = api("GET", "/pay/order/restore-1")
    assert code == 200, body
    order = body["order"]
    assert order["provider_ref"] == "0x" + "ab" * 20
    assert order["meta"]["amount_usdc"] == "19.000000"
    assert order["meta"]["asset"] == "USDC"
