#!/usr/bin/env python3
"""Сверка цен: что написано на витринах и что реально выставляет касса.

Зачем. Цена на странице и цена в кассе — два разных файла. Когда они расходятся,
покупатель платит не то, что прочитал (или упирается в «товар не найден»), и узнаёт
об этом в самый дорогой момент.

    python3 scripts/price_consistency.py            # сверить все витрины
    python3 scripts/price_consistency.py --json
    python3 scripts/price_consistency.py --write docs/PRICES.md   # таблица «источник истины»

Источник истины — `PRODUCTS` в кассе. Скрипт только читает страницы и сообщает
о расхождениях; он ничего не правит.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LANDING = Path("/media/Sruti/iamthat/work/sales/landing")
EXTRA_PAGES = (
    Path("/media/Sruti/iamthat/work/sales/attest/attest/store_page.py"),
)
PRODUCT_RE = re.compile(r"product=([a-z0-9][a-z0-9-]{2,40})")
PRICE_RE = re.compile(r"\$\s?(\d{1,4})(?![\d])")
WINDOW = 260          # сколько символов вокруг ссылки считаем «ценой этой карточки»


def prices() -> dict[str, int]:
    from nidhipati_proof.payment_hub.checkout import PRODUCTS

    return {slug: int(float(spec["price_usd"])) for slug, spec in PRODUCTS.items()}


def page_files() -> list[Path]:
    files: list[Path] = []
    if LANDING.exists():
        files.extend(sorted(LANDING.glob("*/index.html")))
    files.extend(p for p in EXTRA_PAGES if p.exists())
    return files


def scan_text(text: str, known: dict[str, int]) -> list[dict]:
    """Найти ссылки на кассу и цену рядом с каждой. Возвращает замечания."""
    issues: list[dict] = []
    for match in PRODUCT_RE.finditer(text):
        slug = match.group(1)
        window = text[max(0, match.start() - WINDOW): match.end() + WINDOW]
        found = sorted({int(m) for m in PRICE_RE.findall(window)})
        if slug not in known:
            issues.append({"level": "error", "slug": slug,
                           "why": "товара нет в кассе — кнопка приведёт к 404"})
            continue
        expected = known[slug]
        if not found:
            issues.append({"level": "warn", "slug": slug,
                           "why": f"рядом с ссылкой не нашлось цены (в кассе ${expected})"})
        elif expected not in found:
            issues.append({"level": "error", "slug": slug,
                           "why": f"на странице ${found}, в кассе ${expected}"})
    return issues


def run(files: list[Path] | None = None) -> dict:
    known = prices()
    files = files if files is not None else page_files()
    report: list[dict] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for issue in scan_text(text, known):
            report.append({**issue, "page": str(path)})
    errors = [r for r in report if r["level"] == "error"]
    return {"pages": len(files), "issues": report, "errors": len(errors),
            "ok": not errors, "products_in_cashier": len(known)}


def write_table(path: Path, data: dict | None = None) -> Path:
    """Таблица цен из кассы — чтобы витрину правили по одному источнику."""
    known = prices() if not data else data
    lines = ["# Цены (источник: касса nidhipati)", "",
             "| Товар | Цена USD |", "|---|---|"]
    lines += [f"| `{slug}` | ${price} |" for slug, price in sorted(known.items())]
    lines += ["", "Сверка: `python3 scripts/price_consistency.py`."]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", default="")
    a = ap.parse_args()
    if a.write:
        print("записано:", write_table(Path(a.write)))
    res = run()
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"страниц: {res['pages']} · товаров в кассе: {res['products_in_cashier']}")
        for issue in res["issues"]:
            mark = "✗" if issue["level"] == "error" else "?"
            print(f"  {mark} {issue['slug']}: {issue['why']} [{Path(issue['page']).name}]")
        print("итог: " + ("цены сходятся" if res["ok"] else f"расхождений: {res['errors']}"))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
