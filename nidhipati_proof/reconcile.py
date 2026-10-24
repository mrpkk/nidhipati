"""Reconcile stablecoin invoices against transactions.

Why: a treasury spreadsheet and a wallet export are two lists of the same money
that never quite agree. This matches them by amount, asset, memo and time, and
names what is left over in both directions: invoices nobody paid, receipts nobody
invoiced, invoices paid twice.

Honest boundary: no chain read, no custody, no private keys. The match is a
weighing of two files, not a movement of funds.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

INVOICE_COLUMNS = ("id", "amount", "asset", "created_at")
TX_COLUMNS = ("tx_hash", "amount", "asset", "timestamp")
DEFAULT_DUE_DAYS = 30
GRACE_DAYS = 1


@dataclass
class Invoice:
    id: str
    amount: Decimal
    asset: str
    created_at: datetime
    due_at: datetime | None = None
    payee: str = ""
    memo: str = ""


@dataclass
class Tx:
    tx_hash: str
    amount: Decimal
    asset: str
    ts: datetime
    to: str = ""
    memo: str = ""


@dataclass
class Match:
    invoice: Invoice
    tx: Tx
    basis: str            # memo | amount
    late: bool = False

    def as_row(self) -> dict[str, str]:
        return {
            "invoice_id": self.invoice.id,
            "tx_hash": self.tx.tx_hash,
            "amount": str(self.tx.amount),
            "asset": self.tx.asset,
            "status": "late" if self.late else "matched",
            "basis": self.basis,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "invoice_id": self.invoice.id,
            "tx_hash": self.tx.tx_hash,
            "amount": str(self.tx.amount),
            "asset": self.tx.asset,
            "basis": self.basis,
            "late": self.late,
        }


@dataclass
class ReconcileReport:
    matches: list[Match] = field(default_factory=list)
    unpaid: list[Invoice] = field(default_factory=list)
    unmatched_receipts: list[Tx] = field(default_factory=list)
    findings: list[dict[str, str]] = field(default_factory=list)
    disclaimer: str = (
        "Two files were compared; nothing was read from chain and no funds were moved. "
        "A match by amount and time is a strong hint, not proof — confirm against the "
        "provider before closing the books."
    )

    def add(self, code: str, severity: str, detail: str, ref: str = "") -> None:
        self.findings.append({"code": code, "severity": severity, "ref": ref, "detail": detail})

    def errors(self) -> list[dict[str, str]]:
        return [f for f in self.findings if f["severity"] == "error"]

    @property
    def matched_total(self) -> Decimal:
        return sum((m.tx.amount for m in self.matches), Decimal("0"))

    @property
    def unpaid_total(self) -> Decimal:
        return sum((i.amount for i in self.unpaid), Decimal("0"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "invoices": len(self.matches) + len(self.unpaid),
            "matched": len(self.matches),
            "unpaid": len(self.unpaid),
            "unmatched_receipts": len(self.unmatched_receipts),
            "matched_total": str(self.matched_total),
            "unpaid_total": str(self.unpaid_total),
            "matches": [m.as_dict() for m in self.matches],
            "unpaid_invoices": [
                {"id": i.id, "amount": str(i.amount), "asset": i.asset,
                 "created_at": i.created_at.isoformat()} for i in self.unpaid],
            "unmatched_receipts": [
                {"tx_hash": t.tx_hash, "amount": str(t.amount), "asset": t.asset,
                 "timestamp": t.ts.isoformat()} for t in self.unmatched_receipts],
            "findings": self.findings,
            "disclaimer": self.disclaimer,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Reconciliation report",
            "",
            f"Invoices **{len(self.matches) + len(self.unpaid)}** · matched **{len(self.matches)}** "
            f"(**{self.matched_total}**) · unpaid **{len(self.unpaid)}** (**{self.unpaid_total}**) · "
            f"receipts without an invoice **{len(self.unmatched_receipts)}**",
            "",
            "## Matched",
            "",
            "| Invoice | Amount | Asset | Tx | Basis | Late |",
            "|---|---|---|---|---|---|",
        ]
        for m in self.matches:
            lines.append(f"| {m.invoice.id} | {m.tx.amount} | {m.tx.asset} | "
                         f"`{m.tx.tx_hash}` | {m.basis} | {'yes' if m.late else 'no'} |")
        if self.unpaid:
            lines += ["", "## Invoices with no matching transfer", "",
                      "| Invoice | Amount | Asset | Created |", "|---|---|---|---|"]
            for i in self.unpaid:
                lines.append(f"| {i.id} | {i.amount} | {i.asset} | {i.created_at.date()} |")
        if self.unmatched_receipts:
            lines += ["", "## Receipts with no invoice", "",
                      "| Tx | Amount | Asset | Time |", "|---|---|---|---|"]
            for t in self.unmatched_receipts:
                lines.append(f"| `{t.tx_hash}` | {t.amount} | {t.asset} | {t.ts.isoformat()} |")
        lines += ["", "## Findings", ""]
        if not self.findings:
            lines += ["No finding: every invoice has exactly one transfer and every transfer has "
                      "an invoice.", ""]
        else:
            lines += ["| Severity | Code | Ref | Detail |", "|---|---|---|---|"]
            for f in self.findings:
                lines.append(f"| {f['severity']} | `{f['code']}` | {f['ref'] or '—'} | {f['detail']} |")
            lines.append("")
        lines += [f"> {self.disclaimer}", ""]
        return "\n".join(lines)

    def write_csv(self, path: str | Path) -> None:
        with Path(path).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["invoice_id", "tx_hash", "amount", "asset", "status", "basis"])
            writer.writeheader()
            for m in self.matches:
                writer.writerow(m.as_row())


def _dec(value: Any, what: str) -> Decimal:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"{what} is not a number: {value!r}") from exc


def _ts(value: Any, what: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{what} is not ISO-8601: {value!r}") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _rows(path: str | Path, required: Iterable[str]) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise ValueError(f"no such file: {p}")
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("rows") or data.get("records") or []
        if not isinstance(data, list) or not data:
            raise ValueError(f"{p.name}: expected a non-empty array of rows")
        return [dict(r) for r in data]
    with p.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{p.name}: missing columns: {', '.join(missing)}")
        rows = [dict(r) for r in reader]
    if not rows:
        raise ValueError(f"{p.name}: no rows")
    return rows


def invoice_from_row(raw: dict[str, Any]) -> Invoice:
    missing = [c for c in INVOICE_COLUMNS if str(raw.get(c) or "").strip() == ""]
    if missing:
        raise ValueError(f"invoice: empty {', '.join(missing)}")
    return Invoice(
        id=str(raw["id"]).strip(),
        amount=_dec(raw["amount"], "invoice amount"),
        asset=str(raw["asset"]).strip().upper(),
        created_at=_ts(raw["created_at"], "invoice created_at"),
        due_at=_ts(raw["due_at"], "invoice due_at") if raw.get("due_at") else None,
        payee=str(raw.get("payee") or "").strip(),
        memo=str(raw.get("memo") or "").strip(),
    )


def tx_from_row(raw: dict[str, Any]) -> Tx:
    missing = [c for c in TX_COLUMNS if str(raw.get(c) or "").strip() == ""]
    if missing:
        raise ValueError(f"transaction: empty {', '.join(missing)}")
    return Tx(
        tx_hash=str(raw["tx_hash"]).strip(),
        amount=_dec(raw["amount"], "tx amount"),
        asset=str(raw["asset"]).strip().upper(),
        ts=_ts(raw["timestamp"], "tx timestamp"),
        to=str(raw.get("to") or "").strip(),
        memo=str(raw.get("memo") or "").strip(),
    )


def load_invoices(path: str | Path) -> list[Invoice]:
    return [invoice_from_row(raw) for raw in _rows(path, INVOICE_COLUMNS)]


def load_transactions(path: str | Path) -> list[Tx]:
    return [tx_from_row(raw) for raw in _rows(path, TX_COLUMNS)]


def _window(invoice: Invoice) -> tuple[datetime, datetime]:
    due = invoice.due_at or invoice.created_at + timedelta(days=DEFAULT_DUE_DAYS)
    return invoice.created_at - timedelta(days=GRACE_DAYS), due + timedelta(days=GRACE_DAYS)


def reconcile(invoices: list[Invoice], txs: list[Tx]) -> ReconcileReport:
    report = ReconcileReport()
    used: set[int] = set()
    duplicates: set[int] = set()   # уже названы как повтор, чтобы не считать их дважды

    for invoice in sorted(invoices, key=lambda i: i.created_at):
        start, end = _window(invoice)
        candidates = [
            (idx, tx) for idx, tx in enumerate(txs)
            if idx not in used
            and tx.asset == invoice.asset
            and start <= tx.ts <= end
        ]
        exact = [(i, t) for i, t in candidates if t.amount == invoice.amount]
        memo_hits = [(i, t) for i, t in exact if invoice.id and invoice.id in t.memo]
        memo_any = [(i, t) for i, t in candidates if invoice.id and invoice.id in t.memo]

        if memo_hits or exact:
            idx, tx = (memo_hits or exact)[0]
            basis = "memo" if memo_hits else "amount"
            used.add(idx)
            due = invoice.due_at or invoice.created_at + timedelta(days=DEFAULT_DUE_DAYS)
            late = tx.ts > due
            report.matches.append(Match(invoice, tx, basis, late))
            if late:
                report.add("late_payment", "warning",
                           f"invoice {invoice.id} paid {tx.ts.date()}, due {due.date()}", invoice.id)
            extra = [(i, t) for i, t in exact if i != idx]
            for i, t in extra:
                duplicates.add(i)
                report.add("duplicate_payment", "error",
                           f"invoice {invoice.id} matched by more than one transfer "
                           f"(also {t.tx_hash}): {t.amount} {t.asset}", invoice.id)
            continue

        if memo_any:
            idx, tx = memo_any[0]
            used.add(idx)
            report.add("amount_mismatch", "error",
                       f"invoice {invoice.id} is {invoice.amount} {invoice.asset}, transfer "
                       f"{tx.tx_hash} is {tx.amount} {tx.asset}", invoice.id)
            report.matches.append(Match(invoice, tx, "memo", False))
            continue

        report.unpaid.append(invoice)
        report.add("unpaid_invoice", "error",
                   f"invoice {invoice.id} ({invoice.amount} {invoice.asset}) has no transfer "
                   f"within its window", invoice.id)

    for idx, tx in enumerate(txs):
        if idx not in used and idx not in duplicates:
            report.unmatched_receipts.append(tx)
            report.add("unmatched_receipt", "warning",
                       f"transfer {tx.tx_hash} ({tx.amount} {tx.asset}) matches no invoice",
                       tx.tx_hash)

    # Одинаковый hash дважды — это не два платежа, а ошибка выгрузки.
    seen: dict[str, int] = {}
    for t in txs:
        seen[t.tx_hash] = seen.get(t.tx_hash, 0) + 1
    for tx_hash, count in seen.items():
        if count > 1:
            report.add("duplicate_receipt", "error",
                       f"tx {tx_hash} appears {count} times in the export", tx_hash)
    return report
