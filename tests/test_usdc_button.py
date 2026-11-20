"""USDC-кнопка на audit.html: адрес один и тот же, из ~/.env.

Тест дороже всего стоит здесь: неверный адрес получателя = потерянные деньги
покупателя. Поэтому проверяем и формат, и совпадение с окружением, и то, что
сумма с сетью названы рядом с адресом.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.usdc_block import AMOUNT, ENV, NETWORK, inject, payout_address, block

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "audit.html"
ADDR = re.compile(r"0x[a-fA-F0-9]{40}")
VALID = "0xefCD6886f73064ea9EcbaA4741Ef1309A0885C59"


def test_block_needs_a_real_address():
    for bad in ("", "0x123", "efCD6886f73064ea9EcbaA4741Ef1309A0885C59"):
        with pytest.raises(ValueError):
            block(bad)


def test_block_names_amount_and_network_next_to_address():
    html = block(VALID)
    assert VALID in html
    assert f"{AMOUNT} USDC" in html and NETWORK in html
    # адрес не должен «прятаться» за ссылкой: копируют текст
    assert f"<code class=\"addr\">{VALID}</code>" in html


def test_inject_is_idempotent_and_keeps_one_block():
    html = "<html><body><footer>f</footer></body></html>"
    once = inject(html, VALID)
    twice = inject(once, VALID)
    assert once == twice
    assert once.count("usdc:start") == 1
    assert once.index("usdc:start") < once.index("<footer")


def test_page_has_exactly_one_usdc_block():
    html = PAGE.read_text(encoding="utf-8")
    assert html.count("usdc:start") == 1 and html.count("usdc:end") == 1
    found = ADDR.findall(html)
    assert len(found) == 1, found            # один адрес на странице, а не три разных
    assert f"{AMOUNT} USDC" in html and NETWORK in html


def test_page_address_matches_env():
    env_address = payout_address()
    if not env_address:
        pytest.skip("нет ~/.env с адресом получателя")
    html = PAGE.read_text(encoding="utf-8")
    assert env_address in html, "адрес на странице не совпадает с ~/.env"
    assert payout_address(ENV) == env_address
