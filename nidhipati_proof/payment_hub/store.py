from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import PaymentStatus


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class OrderRecord:
    order_id: str
    product_id: str
    amount_fiat: str
    currency: str
    status: str
    provider: str | None = None
    provider_ref: str | None = None
    checkout_url: str | None = None
    txid_in: str | None = None
    txid_out: str | None = None
    signature_verified: int | None = None
    meta: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PaymentStore:
    """SQLite store for orders/events/idempotency. Thread-safe for basic use."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    amount_fiat TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider TEXT,
                    provider_ref TEXT,
                    checkout_url TEXT,
                    txid_in TEXT,
                    txid_out TEXT,
                    signature_verified INTEGER,
                    meta TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_key TEXT UNIQUE,
                    order_id TEXT,
                    provider TEXT,
                    status TEXT,
                    raw TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS idempotency (
                    key TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                );
                """
            )

    def close(self) -> None:
        self._conn.close()

    def mark_once(self, key: str) -> bool:
        now = _utcnow()
        with self._lock, self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO idempotency(key, created_at) VALUES (?, ?)", (key, now)
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def seen(self, key: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM idempotency WHERE key=?", (key,))
        return cur.fetchone() is not None

    def upsert_order(self, rec: OrderRecord) -> OrderRecord:
        now = _utcnow()
        rec.created_at = rec.created_at or now
        rec.updated_at = now
        meta = json.dumps(rec.meta or {}, ensure_ascii=False, sort_keys=True)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO orders(order_id, product_id, amount_fiat, currency, status, provider, provider_ref,
                                   checkout_url, txid_in, txid_out, signature_verified, meta, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(order_id) DO UPDATE SET
                  product_id=excluded.product_id,
                  amount_fiat=excluded.amount_fiat,
                  currency=excluded.currency,
                  status=excluded.status,
                  provider=excluded.provider,
                  provider_ref=excluded.provider_ref,
                  checkout_url=excluded.checkout_url,
                  txid_in=COALESCE(excluded.txid_in, orders.txid_in),
                  txid_out=COALESCE(excluded.txid_out, orders.txid_out),
                  signature_verified=CASE WHEN excluded.signature_verified IS NULL THEN orders.signature_verified ELSE excluded.signature_verified END,
                  meta=excluded.meta,
                  updated_at=excluded.updated_at
                """,
                (
                    rec.order_id, rec.product_id, rec.amount_fiat, rec.currency, rec.status,
                    rec.provider, rec.provider_ref, rec.checkout_url, rec.txid_in, rec.txid_out,
                    rec.signature_verified, meta, rec.created_at, rec.updated_at,
                ),
            )
        return rec

    def get_order(self, order_id: str) -> OrderRecord | None:
        cur = self._conn.execute("SELECT * FROM orders WHERE order_id=?", (order_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["meta"] = json.loads(d["meta"] or "{}")
        return OrderRecord(**d)

    def record_event(self, *, event_key: str, order_id: str | None, provider: str, status: str, raw: dict[str, Any]) -> bool:
        now = _utcnow()
        with self._lock, self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO events(event_key, order_id, provider, status, raw, created_at) VALUES (?,?,?,?,?,?)",
                    (event_key, order_id, provider, status, json.dumps(raw, ensure_ascii=False, sort_keys=True), now),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def update_status(self, order_id: str, status: str, **fields: Any) -> bool:
        if not self.get_order(order_id):
            return False
        now = _utcnow()
        sets = ["status=?", "updated_at=?"]
        vals: list[Any] = [status, now]
        for k in ("provider", "provider_ref", "checkout_url", "txid_in", "txid_out", "signature_verified"):
            if k in fields and fields[k] is not None:
                sets.append(f"{k}=?")
                vals.append(fields[k])
        if "meta" in fields and fields["meta"] is not None:
            sets.append("meta=?")
            vals.append(json.dumps(fields["meta"], ensure_ascii=False, sort_keys=True))
        vals.append(order_id)
        with self._lock, self._conn:
            self._conn.execute(f"UPDATE orders SET {', '.join(sets)} WHERE order_id=?", vals)
        return True
