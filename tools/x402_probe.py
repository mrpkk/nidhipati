#!/usr/bin/env python3
"""Проверить, отдают ли платные x402-эндпоинты корректный вызов оплаты.

Зачем: агент-клиент платит только тогда, когда получает 402, в теле которого
есть `accepts` (и `x402Version` в v2). Если вместо этого 404, 200, 302 или
402 с пустым телом — клиент не заплатит, и команда об этом не узнает:
в логах это «визит», а не потерянная продажа.

Правило честности: строка результата хранит **точный URL**, статус, тип
содержимого и вердикт. Никаких обрезанных путей — иначе письмо нельзя
проверить повторно.

Запуск:
    python3 tools/x402_probe.py --pages 1 --hosts-csv outreach/targets_agent.csv \
        --out outreach/probe_endpoints.csv
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


GEO_MARKERS = ("sanction", "region-not-supported", "not-supported", "blocked", "geo", "restricted", "forbidden")


def is_geo_redirect(headers: dict[str, str]) -> bool:
    """Редирект «ваш регион не обслуживается» — это отказ нам, а не поломка сервиса.

    Проверка идёт с санкционной сети, и 302/451 здесь означает «вас не пустили»,
    а не «у вас сломан платёж». Считать это дефектом — обвинять невиновного.
    """
    loc = (headers.get("location") or "").lower()
    return bool(loc) and any(m in loc for m in GEO_MARKERS)


def verdict(status: int, body: str, headers: dict[str, str] | None = None) -> tuple[str, str]:
    """Что именно сломалось — словами, которые можно повторить в письме.

    Вызов оплаты по спецификации x402 v2 едет в заголовке PAYMENT-REQUIRED,
    а в теле его может не быть вовсе. Сервис, у которого заголовок на месте,
    исправен, даже если тело пустое: объявлять его сломанным — значит
    обвинять того, кто не виноват.
    """
    h = {k.lower(): v for k, v in (headers or {}).items()}
    if status == 402 and (h.get("payment-required") or h.get("x-payment-required")):
        return "ok", "402 with the PAYMENT-REQUIRED header"
    if status == 402:
        try:
            data = json.loads(body)
        except Exception:
            return "broken", "402 with a body that is not JSON"
        if not isinstance(data, dict):
            return "broken", "402 with a non-object body"
        accepts = data.get("accepts")
        if isinstance(accepts, list) and accepts:
            return "ok", "402 with accepts"
        if isinstance(data.get("x402Version"), int) and accepts:
            return "ok", "402 with accepts"
        if not data:
            return "broken", "402 with an empty body: a client cannot build a payment"
        return "broken", "402 without accepts: a client cannot build a payment"
    if status == 200:
        return "broken", "200 without payment: the paywall did not fire"
    if status in (301, 302, 303, 307, 308):
        if is_geo_redirect(h):
            return "geo", f"{status} to {h.get('location','')[:60]}: the service refuses this region"
        return "broken", f"{status} redirect instead of a payment challenge"
    if status == 410:
        return "broken", "410 Gone: the listed resource no longer exists"
    if status == 404:
        return "broken", "404: the listed path does not exist"
    if status == 451:
        return "legal", "451: unavailable for legal reasons (not a defect)"
    if status == 0:
        return "error", "no response"
    return "broken", f"{status}: not a payment challenge"


async def probe(client: httpx.AsyncClient, url: str, method: str, payload: dict | None, sem: asyncio.Semaphore) -> dict:
    # Шаблон пути (`:address`, `{chainId}`) нельзя проверить без реального значения:
    # ответ 404/410 на заглушку — это свойство заглушки, а не дефект сервиса.
    if ":" in url.split("//", 1)[-1].split("/", 1)[-1] or "{" in url:
        return {"url": url, "method": method, "status": 0, "ctype": "",
                "verdict": "template", "why": "path template: needs a real value to test"}
    async with sem:
        try:
            r = await client.request(method, url, json=payload)
            status, body = r.status_code, r.text[:4000]
            ctype = r.headers.get("content-type", "")
            headers = dict(r.headers)
        except Exception as exc:
            return {"url": url, "method": method, "status": 0, "ctype": "",
                    "verdict": "error", "why": type(exc).__name__}
    v, why = verdict(status, body, headers)
    return {"url": url, "method": method, "status": status, "ctype": ctype.split(";")[0],
            "verdict": v, "why": why}


async def main_async(pages: int, out: Path, limit: int, concurrency: int, only: set[str] | None) -> None:
    items = load(pages)
    by_host: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        bz = (it.get("extensions") or {}).get("bazaar") or {}
        res = it.get("resource") or (bz.get("info") or {}).get("resource") or ""
        host = urlparse(res).hostname
        if not host or (only and host not in only):
            continue
        if len(by_host[host]) < 3:
            by_host[host].append(it)
    targets = list(by_host.items())[:limit]
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA}, follow_redirects=False) as client:
        async def one(host: str, its: list[dict]) -> list[dict]:
            rows = []
            for it in its:
                bz = (it.get("extensions") or {}).get("bazaar") or {}
                info = bz.get("info") or {}
                url = it.get("resource") or info.get("resource") or ""
                method = ((info.get("input") or {}).get("method") or "GET").upper()
                example = (info.get("input") or {}).get("body") or None
                row = await probe(client, url, method, example, sem)
                row["host"] = host
                rows.append(row)
            return rows

        nested = await asyncio.gather(*(one(h, its) for h, its in targets))

    rows = [r for group in nested for r in group]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["host", "method", "url", "status", "ctype", "verdict", "why"])
        w.writeheader()
        w.writerows(rows)
    hosts = {r["host"] for r in rows}
    broken = {r["host"] for r in rows if r["verdict"] == "broken"}
    print(f"хостов: {len(hosts)} · эндпоинтов: {len(rows)} · с дефектом: {len(broken)} · → {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--out", default="outreach/probe_endpoints.csv")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--hosts-csv", default="")
    a = ap.parse_args()
    only = None
    if a.hosts_csv:
        only = {r["host"] for r in csv.DictReader(open(a.hosts_csv)) if r.get("email")}
    asyncio.run(main_async(a.pages, Path(a.out), a.limit, a.concurrency, only))


if __name__ == "__main__":
    main()
