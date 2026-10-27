#!/usr/bin/env python3
"""Список RWA-эмитентов для полосы B: подтверждение резервов.

Зачем именно они: у эмитента токенизированного фонда или стейблкоина есть
публичная обязанность «чем обеспечено» и нет дешёвого способа это доказать,
не раскрывая состав. Наш `reserve` делает ровно это. Крупняк покупает у
Big Four; нам интересны средние — от миллиона до полумиллиарда TVL, где
аудитор дороже продукта.

Источник целей — публичный список DefiLlama (категория RWA). Контакт берётся
только со страницы самой компании или из `/.well-known/security.txt`; ничего
не выдумывается. Если контакта нет — строка остаётся пустой.

Запуск:
    python3 tools/rwa_targets.py --min 1e6 --max 5e8 --out outreach/targets_rwa.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path
from urllib.parse import urlparse

import httpx

from outreach_targets import UA, contact_for

PROTOCOLS = "https://api.llama.fi/protocols"


def load_rwa(min_tvl: float, max_tvl: float) -> list[dict]:
    with httpx.Client(timeout=90, headers={"User-Agent": UA}) as client:
        data = client.get(PROTOCOLS).json()
    out = []
    for item in data:
        if item.get("category") != "RWA":
            continue
        tvl = item.get("tvl") or 0
        url = item.get("url") or ""
        host = urlparse(url).hostname
        if not host or not (min_tvl <= tvl <= max_tvl):
            continue
        out.append({"name": item.get("name") or host, "host": host, "tvl": int(tvl), "url": url})
    out.sort(key=lambda r: -r["tvl"])
    return out


async def main_async(min_tvl: float, max_tvl: float, limit: int, out: Path, concurrency: int) -> None:
    targets = load_rwa(min_tvl, max_tvl)[:limit]
    print(f"RWA в диапазоне: {len(targets)}")
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=12, headers={"User-Agent": UA}) as client:
        rows = await asyncio.gather(*(contact_for(client, t["host"], sem) for t in targets))
    by_host = {r["host"]: r for r in rows}
    final = []
    for t in targets:
        r = by_host[t["host"]]
        final.append({**t, "email": r["email"], "source": r["source"], "status": r["status"]})

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "host", "tvl", "url", "email", "source", "status"])
        w.writeheader()
        w.writerows(final)
    found = sum(1 for r in final if r["email"])
    print(f"контакт найден: {found}/{len(final)} · → {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=1e6)
    ap.add_argument("--max", type=float, default=5e8)
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--out", default="outreach/targets_rwa.csv")
    ap.add_argument("--concurrency", type=int, default=8)
    a = ap.parse_args()
    asyncio.run(main_async(a.min, a.max, a.limit, Path(a.out), a.concurrency))


if __name__ == "__main__":
    main()
