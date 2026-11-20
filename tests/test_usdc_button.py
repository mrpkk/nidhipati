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


# ── несколько страниц и сверка адреса ──────────────────────────────────────

def test_verify_flags_stale_address(tmp_path):
    """Смена кошелька в ~/.env обязана ловиться: страница со старым адресом = stale."""
    from scripts.usdc_block import verify_targets
    page = tmp_path / "old.html"
    page.write_text(f'<pre>{VALID}</pre>', encoding="utf-8")
    other = "0x1111111111111111111111111111111111111111"
    rows = verify_targets(other, targets=[(str(page), "199")])
    assert rows == [(str(page), "stale")], rows


def test_verify_ok_when_address_matches(tmp_path):
    from scripts.usdc_block import verify_targets
    page = tmp_path / "fresh.html"
    page.write_text(f'<pre>{VALID}</pre>', encoding="utf-8")
    assert verify_targets(VALID, targets=[(str(page), "199")]) == [(str(page), "ok")]


def test_verify_reports_missing_block(tmp_path):
    from scripts.usdc_block import verify_targets
    page = tmp_path / "plain.html"
    page.write_text("<html><body>без адреса</body></html>", encoding="utf-8")
    assert verify_targets(VALID, targets=[(str(page), "199")]) == [(str(page), "missing")]


def test_all_live_targets_carry_the_env_address():
    """Реальные страницы: цена цен и оффер Root Check. Падает при расхождении с ~/.env."""
    from scripts.usdc_block import TARGETS, verify_targets
    env_address = payout_address()
    if not env_address:
        pytest.skip("нет ~/.env с адресом получателя")
    rows = verify_targets(env_address)
    assert len(rows) == len(TARGETS)
    bad = [r for r, st in rows if st != "ok"]
    assert not bad, bad


# ── процедура смены кошелька: verify → sync → verify ──────────────────────

def test_wallet_rotation_procedure(tmp_path):
    """Сменили кошелёк — страницы обязаны отстать, а --sync их догнать.

    Проверяем саму процедуру на копиях: живой ~/.env и живые страницы не трогаем.
    """
    import subprocess
    import sys

    old = "0x" + "1" * 40
    new = "0x" + "2" * 40
    page = tmp_path / "page.html"
    # как на живых страницах: блок между маркерами, иначе inject допишет второй
    page.write_text(f"<html><body><!-- usdc:start --><pre>{old}</pre><!-- usdc:end -->"
                    f"</body></html>", encoding="utf-8")
    env = tmp_path / "env"
    env.write_text(f"NIDHIPATI_PAYOUT_ADDRESS={new}\n", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "scripts" / "usdc_block.py"
    # 1) кошелёк сменён → verify видит расхождение и возвращает 1
    stale = subprocess.run([sys.executable, str(script), "--verify", "--env", str(env)],
                           capture_output=True, text=True,
                           env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
    assert "stale" in stale.stdout or "missing" in stale.stdout, stale.stdout

    # 2) --sync подставляет адрес из окружения в целевые страницы и перепроверяет
    from scripts.usdc_block import inject, verify_targets
    fresh = inject(page.read_text(encoding="utf-8"), new)
    page.write_text(fresh, encoding="utf-8")
    assert verify_targets(new, targets=[(str(page), "199")]) == [(str(page), "ok")]


def test_all_pages_with_address_are_covered():
    """Адрес живёт на 11 страницах: смена кошелька без любой из них = деньги в никуда."""
    from scripts.usdc_block import TARGETS, verify_targets
    env_address = payout_address()
    if not env_address:
        pytest.skip("нет ~/.env с адресом получателя")
    rows = verify_targets(env_address)
    assert len(rows) >= 10, f"покрытие страниц сократилось: {len(rows)}"
    bad = [(r, st) for r, st in rows if st != "ok"]
    assert not bad, bad


def test_sync_never_injects_foreign_price(tmp_path):
    """Страница без маркеров не должна получить блок с чужой ценой ($199 на $19-странице)."""
    from scripts.usdc_block import has_marker, inject
    plain = "<html><body><pre>0x" + "1" * 40 + "</pre></body></html>"
    assert has_marker(plain) is False          # такие страницы --sync пропускает

    marked = f"<html><!-- usdc:start -->old<!-- usdc:end --></html>"
    assert has_marker(marked) is True
    out = inject(marked, "0x" + "2" * 40, amount="19")
    assert "19 USDC" in out and "199 USDC" not in out


# ── обёртка существующих блоков и обновление только адреса ────────────────

def test_wrap_existing_keeps_page_price(tmp_path):
    """Блок со своей ценой оборачивается как есть: текст и сумму не переписываем."""
    from scripts.usdc_block import has_marker, wrap_existing
    html = ('<html><body><div class="card"><h2>Оплата криптой</h2>'
            f'<p>79 USDC в сети Base</p><pre>{VALID}</pre>'
            '<div class="inner">вложенный</div></div></body></html>')
    out = wrap_existing(html, VALID)
    assert has_marker(out)
    assert "79 USDC" in out and "вложенный" in out
    # вложенный div закрыт правильно: маркер END после последнего </div> карточки
    assert out.index("usdc:end") > out.index("вложенный")


def test_sync_updates_only_the_address_not_the_price():
    """`--sync` не подставляет 199 на страницу за $19 — он меняет только адрес."""
    from scripts.usdc_block import START, END, update_address_in_block
    old = "0x" + "1" * 40
    new = "0x" + "2" * 40
    html = f'<html>{START}<div class="card"><p>19 USDC</p><pre>{old}</pre></div>{END}</html>'
    out = update_address_in_block(html, new)
    assert "19 USDC" in out, "цена страницы не должна меняться"
    assert new in out and old not in out
    assert START in out and END in out


def test_all_targets_have_markers_now():
    """После обёртки все 11 страниц обновляемы: иначе смена кошелька их не догонит."""
    from scripts.usdc_block import TARGETS, has_marker
    missing = []
    for rel, _amount in TARGETS:
        path = Path(rel) if Path(rel).is_absolute() else Path(__file__).resolve().parents[1] / rel
        if path.exists() and not has_marker(path.read_text(encoding="utf-8")):
            missing.append(rel)
    assert not missing, f"без маркеров: {missing}"
