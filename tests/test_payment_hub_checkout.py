"""Витрина оплаты: страница чека отдаётся, неизвестный продукт — нет."""
from __future__ import annotations

import pytest

from nidhipati_proof.payment_hub.checkout import PRODUCTS, checkout_page


def test_audit_product_has_a_checkout_page():
    page = checkout_page("agent-spend-audit")
    assert page is not None
    html, title, price = page
    assert title == "Agent Spend Audit"
    assert price == "500"
    assert "500" in html
    # Страница не обещает выдачу автоматом: выдача остаётся ручной.
    assert "intake form" in html.lower()
    assert "noindex" in html


def test_unknown_product_has_no_page():
    assert checkout_page("does-not-exist") is None


def test_page_carries_both_rails_of_the_flow():
    """Страница зовёт оба эндпоинта хаба: создание заказа и подтверждение."""
    html, _t, _p = checkout_page("agent-spend-audit")
    assert "/pay/create" in html
    assert "/pay/confirm" in html


def test_every_product_has_a_summary_and_delivery():
    for key, spec in PRODUCTS.items():
        assert spec["title"] and spec["summary"] and spec["delivery"], key
        assert spec["price_usd"].replace(".", "").isdigit(), key
