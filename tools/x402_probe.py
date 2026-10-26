#!/usr/bin/env python3
"""Проверить, отдают ли платные x402-эндпоинты корректный 402 без оплаты.

Зачем: агент-клиент платит только тогда, когда получает корректный вызов 402
с телом, где есть `x402Version` и `accepts`. Если вместо этого приходит 200,
404 или 500, клиент не заплатит — и команда теряет выручку, не зная об этом.

Это проверка только публичного поведения: один неавторизованный запрос на
эндпоинт, без обхода оплаты и без нагрузки.

Запуск:
    python3 tools/x402_probe.py --pages 1 --out outreach/probe.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import httpx

DISCOVERY = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"
UA = "attest-audit/1.0 (+https://attest.rta.lat)"


def load(pages: int) -> list[dict]:
    out: list[dict] = []
    with httpx.Client(timeout=90, headers={"User-Agent": UA}) as c:
        for page in range(pages):
            data = c.get(DISCOVERY, params={"limit": 1000, "offset": page * 1000}).json()
            out += data.get("items", [])
    return out


def shape(body: str) -> tuple[bool, str]:
    try:
        data = json.loads(body)
    except Exception:
        return False, "not-json"
    if not isinstance(data, dict):
        return False, "not-object"
    has_version = "x402Version" in data
    has_accepts = isinstance(data.get("accepts"), list) and bool(data.get("accepts"))
    if has_version and has_accepts:
        return True, "ok"
    missing = []
    if not has_version:
        missing.append("x402Version")
    if not has_accepts:
        missing.append("accepts")
    return False, "missing:" + ",".join(missing)


async def probe(client: httpx.AsyncClient, item: dict) -> dict:
    bazaar = (item.get("extensions") or {}).get("bazaar") or {}
    info = bazaar.get("info") or {}
    resource = item.get("resource") or info.get("resource") or ""
    method = ((info.get("input") or {}).get("method") or "GET").upper()
    ext = (item.get("extensions") or {}).get("bazaar") or {}
    body = (ext.get("schema") or {}).get("properties", {}).get("input", {}).get("properties", {}).get("body", {})
    payload = None
    if body and method in ("POST", "PUT", "PATCH"):
        example = (info.get("input") or {}).get("body") or {}
        payload = example or {}
    try:
        r = await client.request(method, resource, json=payload if payload is not None else None)
    except Exception as exc:
        return {"resource": resource, "method": method, "status": 0, "ok": False, "why": type(exc).__name__}
    ok, why = shape(r.text) if r.status_code == 402 else (False, f"status {r.status_code}")
    return {"resource": resource, "method": method, "status": r.status_code, "ok": ok, "why": why}


async def main_async(pages: int, out: Path, limit: int, concurrency: int, only: set[str] | None) -> None:
    items = load(pages)
    by_host = defaultdict(list)
    for it in items:
        bazaar = (it.get("extensions") or {}).get("bazaar") or {}
        res = it.get("resource") or (bazaar.get("info") or {}).get("resource") or ""
        host = urlparse(res).hostname
        if not host or (only and host not in only):
            continue
        if len(by_host[host]) < 5:
            by_host[host].append(it)
    targets = list(by_host.items())[:limit]
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA}, follow_redirects=False) as client:
        async def one(host: str, its: list[dict]) -> list[dict]:
            async with sem:
                return [await probe(client, it) for it in its]

        results = await asyncio.gather(*(one(h, its) for h, its in targets))

    rows = []
    for (host, _), res in zip(targets, results):
        bad = [r for r in res if not r["ok"]]
        rows.append({
            "host": host,
            "checked": len(res),
            "bad": len(bad),
            "why": ";".join(f"{r['method']} {r['resource'].split('/')[-1][:24]}: {r['why']}" for r in bad[:3]),
        })
    rows.sort(key=lambda r: (-r["bad"], r["host"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["host", "checked", "bad", "why"])
        w.writeheader()
        w.writerows(rows)
    broken = sum(1 for r in rows if r["bad"])
    print(f"хостов проверено: {len(rows)} · с дефектами: {broken} · → {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--out", default="outreach/probe.csv")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--hosts-csv", default="", help="проверять только хосты с контактом")
    a = ap.parse_args()
    only = None
    if a.hosts_csv:
        only = {r["host"] for r in csv.DictReader(open(a.hosts_csv)) if r.get("email")}
    asyncio.run(main_async(a.pages, Path(a.out), a.limit, a.concurrency, only))


if __name__ == "__main__":
    main()
