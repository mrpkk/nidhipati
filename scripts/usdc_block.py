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
]
ENV = Path.home() / ".env"
AMOUNT = "199"
NETWORK = "Base"
START, END = "<!-- usdc:start -->", "<!-- usdc:end -->"
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")      # проверка одного значения
FIND_RE = re.compile(r"0x[a-fA-F0-9]{40}")           # поиск адресов внутри HTML

_KEYS = ("NIDHIPATI_PAYOUT_ADDRESS", "X402_PAY_TO", "WALLET_BINANCE_USDC_BASE")


def payout_address(env_path: Path = ENV) -> str:
    """Адрес получателя из ~/.env. Порядок ключей — от самого точного к общему."""
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


def inject(html: str, address: str) -> str:
    """Ставит блок на место маркеров; без маркеров — перед <footer>."""
    new = block(address)
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
    a = ap.parse_args()
    address = payout_address()
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

    for rel, _amount in TARGETS:
        path = Path(rel) if Path(rel).is_absolute() else ROOT / rel
        if not path.exists():
            print(f"{rel}: НЕ СУЩЕСТВУЕТ")
            continue
        html = path.read_text(encoding="utf-8")
        updated = inject(html, address)
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
