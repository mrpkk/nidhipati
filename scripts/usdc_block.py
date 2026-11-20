#!/usr/bin/env python3
"""USDC-блок на страницах Nidhipati: адрес берётся из ~/.env, а не из головы.

Зачем генератор, а не правка руками: адрес получателя — единственное поле на
странице, ошибка в котором стоит денег покупателя. Один источник (`~/.env`),
одна функция, маркеры в HTML — блок можно перегенерировать и не бояться, что
на одной странице адрес старый, а на другой новый.

    python3 scripts/usdc_block.py --check   # показать, что было бы записано
    python3 scripts/usdc_block.py           # записать во все страницы docs/

Маркеры в HTML: <!-- usdc:start --> … <!-- usdc:end -->
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Все страницы, где человек платит USDC. Репозиторий — источник, лендинги
# раздаются копиями; адрес в обоих местах обязан совпадать с ~/.env.
TARGETS = [
    ("docs/audit.html", "199"),
    ("docs/pricing.html", "199"),
    ("/media/Sruti/iamthat/work/sales/landing/root-check/index.html", "199"),
    # Ниже — офферы, которые тоже показывают адрес. Смена кошелька без них
    # означает, что человек платит на старый адрес, а мы этого не заметили.
    ("/media/Sruti/iamthat/work/sales/landing/drift-offer/index.html", "79"),
    ("/media/Sruti/iamthat/work/sales/landing/aibiz-review/index.html", "49"),
    ("/media/Sruti/iamthat/work/sales/landing/karta-report/index.html", "19"),
    ("/media/Sruti/iamthat/work/sales/landing/crypto-mcp/index.html", "19"),
    ("/media/Sruti/iamthat/work/sales/landing/data-rescue/index.html", "0"),
    ("/media/Sruti/iamthat/work/sales/landing/data-rescue-kit/index.html", "29"),
    ("/media/Sruti/iamthat/work/sales/landing/pdf-to-excel/index.html", "0"),
    ("/media/Sruti/iamthat/work/sales/landing/wordpress-fix/index.html", "0"),
]
ENV = Path.home() / ".env"
AMOUNT = "199"
NETWORK = "Base"
START, END = "<!-- usdc:start -->", "<!-- usdc:end -->"
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")      # проверка одного значения
FIND_RE = re.compile(r"0x[a-fA-F0-9]{40}")           # поиск адресов внутри HTML

_KEYS = ("NIDHIPATI_PAYOUT_ADDRESS", "X402_PAY_TO", "WALLET_BINANCE_USDC_BASE")


def payout_address(env_path: Path | None = None) -> str:
    """Адрес получателя из ~/.env. Порядок ключей — от самого точного к общему."""
    env_path = env_path or ENV
    try:
        text = env_path.read_text()
    except OSError:
        return ""
    values: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Z0-9_]+)=[\"']?([^\"'\n]*)", line)
        if m:
            values[m.group(1)] = m.group(2).strip()
    for key in _KEYS:
        addr = values.get(key, "")
        if ADDRESS_RE.match(addr):
            return addr
    return ""


def block(address: str, amount: str = AMOUNT, network: str = NETWORK) -> str:
    """HTML блока. Без адреса блок не рисуется — молча неверный адрес хуже пустого."""
    if not ADDRESS_RE.match(address or ""):
        raise ValueError("нужен адрес 0x… из 40 hex")
    return f"""{START}
<section class="card" id="usdc">
  <h2>Pay in USDC — {amount} on {network}</h2>
  <p>Send exactly <b>{amount} USDC</b> on <b>{network}</b> to:</p>
  <p><code class="addr">{address}</code></p>
  <p class="micro">Same network, same amount: a transfer on another chain or for another sum
  cannot be matched to the order. After sending, email the transaction hash to
  <a href="mailto:maxim.pkk@gmail.com?subject=Nidhipati%20USDC%20payment">maxim.pkk@gmail.com</a> —
  the order starts when the transfer is seen on-chain.</p>
</section>
{END}"""


def has_marker(html: str) -> bool:
    return START in html and END in html


def inject(html: str, address: str, amount: str = AMOUNT) -> str:
    """Ставит блок на место маркеров; без маркеров — перед <footer>.

    Цена — параметр: на странице за $19 блок с «199 USDC» был бы обманом, и
    раньше `--sync` подставлял всем одну сумму.
    """
    new = block(address, amount=amount)
    if START in html and END in html:
        head, rest = html.split(START, 1)
        _, tail = rest.split(END, 1)
        return head + new + tail
    if "<footer" in html:
        i = html.index("<footer")
        return html[:i] + new + "\n" + html[i:]
    return html + "\n" + new


def verify_targets(address: str, targets=None) -> list[tuple[str, str]]:
    """(страница, статус): ok | stale | missing. stale — адрес не тот, что в ~/.env."""
    rows = []
    for rel, _amount in (targets or TARGETS):
        path = Path(rel) if Path(rel).is_absolute() else ROOT / rel
        if not path.exists():
            rows.append((rel, "absent"))
            continue
        found = set(FIND_RE.findall(path.read_text(encoding="utf-8")))
        if not found:
            rows.append((rel, "missing"))
        elif found == {address}:
            rows.append((rel, "ok"))
        else:
            rows.append((rel, "stale"))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="только сверить адрес на всех страницах с ~/.env")
    ap.add_argument("--sync", action="store_true",
                    help="обновить страницы и сразу проверить (процедура смены кошелька)")
    ap.add_argument("--env", default="", help="другой файл окружения (для проверки процедуры)")
    a = ap.parse_args()
    address = payout_address(Path(a.env) if a.env else None)
    if not address:
        print("нет адреса в ~/.env (NIDHIPATI_PAYOUT_ADDRESS / X402_PAY_TO)", file=sys.stderr)
        return 2
    if a.verify:
        rows = verify_targets(address)
        for rel, status in rows:
            print(f"{status:8} {rel}")
        bad = [r for r, st in rows if st in ("stale", "missing", "absent")]
        print(f"адрес: {address[:10]}…{address[-4:]}")
        return 1 if bad else 0

    skipped: list[str] = []
    if a.sync:
        for rel, _amount in TARGETS:
            path = Path(rel) if Path(rel).is_absolute() else ROOT / rel
            if not path.exists():
                print(f"{rel}: НЕ СУЩЕСТВУЕТ")
                continue
            html = path.read_text(encoding="utf-8")
            if not has_marker(html):
                # Без маркеров не трогаем: у страниц разные цены ($19/$29/$49/$79),
                # и вставка блока с одной суммой была бы обманом покупателя.
                print(f"пропуск (нет маркеров usdc:start/end): {rel}")
                skipped.append(rel)
                continue
            updated = inject(html, address, amount=_amount)
            if updated != html:
                path.write_text(updated, encoding="utf-8")
                print(f"обновлён: {rel}")
        rows = verify_targets(address)
        for rel, status in rows:
            print(f"{status:8} {rel}")
        bad = [r for r, st in rows if st != "ok"]
        print(f"адрес: {address[:10]}…{address[-4:]}")
        if skipped:
            print(f"пропущено без маркеров: {len(skipped)} — им нужен блок с их ценой вручную")
        return 1 if bad else 0

    for rel, _amount in TARGETS:
        path = Path(rel) if Path(rel).is_absolute() else ROOT / rel
        if not path.exists():
            print(f"{rel}: НЕ СУЩЕСТВУЕТ")
            continue
        html = path.read_text(encoding="utf-8")
        if not has_marker(html):
            print(f"{rel}: нет маркеров — пропуск (цена страницы не 199)")
            continue
        updated = inject(html, address, amount=_amount)
        if a.check:
            print(f"{rel}: {'уже так' if updated == html else 'будет обновлён'}")
            continue
        if updated != html:
            path.write_text(updated, encoding="utf-8")
            print(f"{rel}: обновлён")
        else:
            print(f"{rel}: без изменений")
    print(f"адрес: {address[:10]}…{address[-4:]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
