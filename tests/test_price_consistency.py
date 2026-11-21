"""Цены на витринах и в кассе не должны расходиться.

22.11.2026: цены живут в двух файлах — PRODUCTS в кассе и текст на страницах.
Расхождение (или товар, которого касса не знает) находят уже после клика.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("price_consistency",
                                               ROOT / "scripts" / "price_consistency.py")
pc = importlib.util.module_from_spec(_spec)
sys.modules["price_consistency"] = pc
_spec.loader.exec_module(pc)

KNOWN = {"karta-report": 19, "drift-kill-switch": 79, "agent-spend-audit": 199}


def test_matching_price_passes():
    text = '<a href="https://x/pay/card?product=karta-report">Buy report — $19</a>'
    assert pc.scan_text(text, KNOWN) == []


def test_wrong_price_is_an_error():
    text = '<a href="https://x/pay/card?product=karta-report">Buy report — $49</a>'
    issues = pc.scan_text(text, KNOWN)
    assert issues and issues[0]["level"] == "error"
    assert "49" in issues[0]["why"] and "19" in issues[0]["why"]


def test_unknown_product_is_an_error():
    text = '<a href="https://x/pay/card?product=not-a-product">$19</a>'
    issues = pc.scan_text(text, KNOWN)
    assert issues[0]["level"] == "error" and "нет в кассе" in issues[0]["why"]


def test_link_without_price_nearby_is_a_warning_not_an_error():
    text = '<a href="https://x/pay/card?product=karta-report">Buy</a>' + " " * 800
    issues = pc.scan_text(text, KNOWN)
    assert issues[0]["level"] == "warn"


def test_founding_price_and_old_price_both_visible():
    """Якорь «было $199, стало $19» — законно: сверяем новую цену."""
    text = '<s>$199</s> $19 <a href="https://x/pay/card?product=agent-spend-audit">Start</a>'
    assert pc.scan_text(text, KNOWN) == []


def test_live_landing_pages_match_the_cashier():
    """Живая проверка: все кнопки оплаты ведут на товар с той же ценой."""
    res = pc.run()
    assert res["pages"] >= 10, res["pages"]
    assert res["ok"] is True, res["issues"]


def test_price_table_written_from_cashier(tmp_path):
    target = pc.write_table(tmp_path / "PRICES.md")
    text = target.read_text(encoding="utf-8")
    assert "`karta-report` | $19" in text
    assert "источник: касса" in text
