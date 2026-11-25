"""«Founding-цена для первых 10» — лимит в коде, а не в тексте (26.11.2026).

Почему: оффер обещал первые 10 мест, но касса не считала проданные — 11-й покупатель
получал бы $19, а витрина утверждала бы обратное.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nidhipati_proof.payment_hub.checkout import (  # noqa: E402
    FOUNDING_PRODUCT, FOUNDING_SEATS, FULL_PRODUCT, PRODUCTS, founding_seats_left,
)
from nidhipati_proof.payment_hub.store import OrderRecord, PaymentStore  # noqa: E402


def _paid(store, product, n):
    for i in range(n):
        store.upsert_order(OrderRecord(order_id=f"{product}-{i}", product_id=product,
                                       amount_fiat="19", currency="USD", status="paid",
                                       provider="test", provider_ref=f"r{i}"))


def test_seats_start_full_and_decrease_with_paid_orders():
    store = PaymentStore()
    assert founding_seats_left(store) == FOUNDING_SEATS
    _paid(store, FOUNDING_PRODUCT, 3)
    assert founding_seats_left(store) == FOUNDING_SEATS - 3


def test_unpaid_orders_do_not_consume_a_seat():
    store = PaymentStore()
    _paid(store, FOUNDING_PRODUCT, FOUNDING_SEATS - 1)
    store.upsert_order(OrderRecord(order_id="pending-1", product_id=FOUNDING_PRODUCT,
                                   amount_fiat="19", currency="USD", status="pending",
                                   provider="test", provider_ref="p1"))
    assert founding_seats_left(store) == 1, "неоплаченный заказ место не занимает"


def test_offer_closes_at_ten():
    store = PaymentStore()
    _paid(store, FOUNDING_PRODUCT, FOUNDING_SEATS)
    assert founding_seats_left(store) == 0
    _paid(store, FOUNDING_PRODUCT, 2)
    assert founding_seats_left(store) == 0, "мест не бывает меньше нуля"


def test_card_page_switches_to_full_price_when_closed():
    src = (ROOT / "nidhipati_proof" / "http_mcp.py").read_text(encoding="utf-8")
    assert "founding_seats_left(get_store())" in src
    assert "product = FULL_PRODUCT" in src
    assert PRODUCTS[FOUNDING_PRODUCT]["price_usd"] == "19"
    assert PRODUCTS[FULL_PRODUCT]["price_usd"] == "199"


def test_counter_failure_does_not_block_a_sale():
    class Broken:
        def count_paid(self, product_id):
            raise RuntimeError("database is locked")

    assert founding_seats_left(Broken()) is None
    src = (ROOT / "nidhipati_proof" / "http_mcp.py").read_text(encoding="utf-8")
    assert "не блокируем оплату из-за счётчика" in src
