#!/usr/bin/env python3
"""Собрать контакты команд, которые уже принимают деньги агентов (x402).

Зачем: письмо «мы делаем аудит расходов агента» никому не нужно, а письмо
«у вас платный x402-сервис, вот две находки в вашем каталоге» нужно. Значит
нужен список тех, у кого x402-сервис есть, — он публичный.

Источник целей: CDP discovery API (Bazaar) — официальный каталог платных
x402-ресурсов. Адрес контакта не выдумывается: он берётся со страницы самой
команды (`mailto:`) или из `/.well-known/security.txt`. Если контакта нет —
строка остаётся пустой и в письма не идёт.

Запуск:
    python3 tools/outreach_targets.py --pages 1 --out outreach/targets_agent.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import httpx

DISCOVERY = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"
UA = "attest-audit/1.0 (+https://attest.rta.lat)"
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
MAILTO_RE = re.compile(r"mailto:([^\"'?>\s]+)")
SKIP_EMAIL = re.compile(r"(sentry|wixpress|example\.|@sentry|\.png|\.jpg|\.gif|\.svg)", re.I)


def hosts_from_discovery(pages: int) -> Counter[str]:
    """Каталог отдаёт максимум 1000 позиций за вызов — идём страницами."""
    counter: Counter[str] = Counter()
    with httpx.Client(timeout=90, headers={"User-Agent": UA}) as c:
        for page in range(pages):
            data = c.get(DISCOVERY, params={"limit": 1000, "offset": page * 1000}).json()
            items = data.get("items", [])
            if not items:
                break
            for item in items:
                bazaar = (item.get("extensions") or {}).get("bazaar") or {}
                resource = item.get("resource") or (bazaar.get("info") or {}).get("resource") or ""
                host = urlparse(resource).hostname
                if host:
                    counter[host] += 1
    return counter


def pick(emails: list[str]) -> str:
    good = [e.strip().strip(".,;:<>") for e in emails if "@" in e and not SKIP_EMAIL.search(e)]
    if not good:
        return ""
    # Предпочитаем общий адрес личному: security@ и hello@ читают, а smith@ уходит в спам.
    for prefix in ("security@", "hello@", "contact@", "info@", "team@", "support@", "sales@"):
        for e in good:
            if e.lower().startswith(prefix):
                return e
    return sorted(good)[0]


async def fetch(client: httpx.AsyncClient, url: str) -> str:
    try:
        r = await client.get(url, follow_redirects=True)
        return r.text if r.status_code == 200 else ""
    except Exception:
        return ""


async def contact_for(client: httpx.AsyncClient, host: str, sem: asyncio.Semaphore) -> dict:
    async with sem:
        sec = await fetch(client, f"https://{host}/.well-known/security.txt")
        home = await fetch(client, f"https://{host}/")
    emails: list[str] = []
    source = ""
    if sec:
        emails += [m.strip() for m in re.findall(r"(?im)^contact:\s*mailto:([^\s]+)", sec)]
        emails += EMAIL_RE.findall(sec)
        if emails:
            source = "security.txt"
    if not emails and home:
        emails += MAILTO_RE.findall(home)
        emails += EMAIL_RE.findall(home)
        if emails:
            source = "homepage"
    email = pick(emails)
    return {"host": host, "email": email, "source": source if email else "", "status": "found" if email else "none"}


def has_mx(domain: str) -> bool:
    try:
        out = subprocess.run(["dig", "+short", "MX", domain], capture_output=True, text=True, timeout=8).stdout
        return bool(out.strip())
    except Exception:
        return False


async def main_async(pages: int, out: Path, concurrency: int) -> None:
    hosts = hosts_from_discovery(pages)
    print(f"hosts: {len(hosts)} (из {pages * 1000} ресурсов)")
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=12, headers={"User-Agent": UA}) as client:
        rows = await asyncio.gather(*(contact_for(client, h, sem) for h in hosts))
    for row in rows:
        row["api_calls"] = hosts[row["host"]]
        local = row["email"].split("@")[1] if "@" in row["email"] else ""
        row["mx"] = "yes" if local and has_mx(local) else ""
    rows.sort(key=lambda r: (-r["api_calls"], r["host"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["host", "email", "source", "status", "api_calls", "mx"])
        w.writeheader()
        w.writerows(rows)
    found = sum(1 for r in rows if r["email"])
    mx = sum(1 for r in rows if r["mx"])
    print(f"контакт найден: {found}/{len(rows)} · MX подтверждён: {mx} · → {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=1, help="страниц по 1000 ресурсов")
    ap.add_argument("--out", default="outreach/targets_agent.csv")
    ap.add_argument("--concurrency", type=int, default=8)
    a = ap.parse_args()
    asyncio.run(main_async(a.pages, Path(a.out), a.concurrency))


if __name__ == "__main__":
    main()
