"""Agent spend audit: find money that left without a reason.

Why this module: a 200 OK is not proof that the charge was right. A team with a
budget in a prompt has no budget — only a hope. This reads the records the team
already has (CSV or JSON) and names the rows where money moved without a
permission, a reason, or a refund.

Honest boundary: every amount here is an *estimate* from the records provided.
Nothing is recovered, and nothing is verified on-chain in v0.2.
"""

from __future__ import annotations

import csv
import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

REQUIRED_COLUMNS = ("ts", "agent_id", "tool", "quote", "settled", "status")

KNOWN_ASSETS = {"USDC", "USDT", "DAI", "PYUSD", "USDG"}
KNOWN_NETWORKS = {
    "base", "eip155:8453",
    "ethereum", "eip155:1",
    "polygon", "eip155:137",
    "arbitrum", "eip155:42161",
    "solana",
}
FAILED_STATUSES = {"failed", "error", "rejected", "timeout", "500", "502", "503"}

DUPLICATE_WINDOW_SECONDS = 120
RUNAWAY_PER_MINUTE = 30
ESCALATION_TOLERANCE = Decimal("0.01")   # 1 %
OVERPAY_MEDIAN_FACTOR = Decimal("3")


@dataclass
class Finding:
    code: str
    severity: str          # error | warning
    row: int
    agent_id: str
    amount: Decimal
    detail: str
    evidence: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "row": self.row,
            "agent_id": self.agent_id,
            "amount_usd": str(self.amount),
            "detail": self.detail,
            "evidence": self.evidence,
        }


@dataclass
class SpendReport:
    rows_read: int = 0
    findings: list[Finding] = field(default_factory=list)
    total_settled: Decimal = Decimal("0")
    estimated_overpay: Decimal = Decimal("0")
    disclaimer: str = (
        "Estimates from the records provided. Nothing was recovered; nothing was "
        "verified on-chain in v0.2. Confirm each row against the provider's invoice "
        "before acting."
    )

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    def as_dict(self) -> dict[str, Any]:
        return {
            "rows_read": self.rows_read,
            "total_settled_usd": str(self.total_settled),
            "estimated_overpay_usd": str(self.estimated_overpay),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "findings": [f.as_dict() for f in self.findings],
            "disclaimer": self.disclaimer,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Agent spend audit",
            "",
            f"Rows read: **{self.rows_read}** · settled **${self.total_settled}** · "
            f"estimated overpay **${self.estimated_overpay}** · "
            f"errors {len(self.errors)}, warnings {len(self.warnings)}",
            "",
        ]
        if not self.findings:
            lines += ["No finding: with these records every charge has a reason, "
                      "a permission and a refund where one was due.", ""]
        else:
            lines += ["| row | code | severity | agent | $ | detail | evidence |",
                      "|---|---|---|---|---|---|---|"]
            for f in self.findings:
                lines.append(
                    f"| {f.row} | `{f.code}` | {f.severity} | {f.agent_id} | "
                    f"{f.amount} | {f.detail} | {f.evidence} |")
            lines.append("")
        lines += [f"> {self.disclaimer}", ""]
        return "\n".join(lines)


def _money(value: Any) -> Decimal:
    if value is None or str(value).strip() == "":
        return Decimal("0")
    try:
        return Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError(f"not a number: {value!r}") from exc


def _ts(value: str) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"ts is not ISO-8601: {value!r}") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_records(path: str | Path) -> list[dict[str, Any]]:
    """Read a CSV or a JSON array. A missing column is an error, not an empty value."""
    p = Path(path)
    if not p.exists():
        raise ValueError(f"no such file: {p}")
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("records") or data.get("rows") or []
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of records (or {'records': [...]})")
        records = [dict(r) for r in data]
    else:
        with p.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"missing columns: {', '.join(missing)}")
            records = [dict(r) for r in reader]

    if not records:
        raise ValueError("no records")
    for i, r in enumerate(records, start=2):
        missing = [c for c in REQUIRED_COLUMNS if str(r.get(c) or "").strip() == ""]
        if missing:
            raise ValueError(f"row {i}: empty {', '.join(missing)}")
    return records


def _row_view(raw: dict[str, Any], row: int) -> dict[str, Any]:
    return {
        "row": row,
        "ts": _ts(raw["ts"]),
        "agent_id": str(raw["agent_id"]).strip(),
        "tool": str(raw["tool"]).strip(),
        "model": str(raw.get("model") or "").strip(),
        "quote": _money(raw.get("quote")),
        "settled": _money(raw.get("settled")),
        "actual": _money(raw["actual"]) if str(raw.get("actual") or "").strip() else None,
        "refund": _money(raw.get("refund")),
        "asset": str(raw.get("asset") or "").strip(),
        "network": str(raw.get("network") or "").strip(),
        "tx_hash": str(raw.get("tx_hash") or "").strip(),
        "payee": str(raw.get("payee") or "").strip(),
        "status": str(raw["status"]).strip().lower(),
    }


def audit(records: Iterable[dict[str, Any]], policy: dict[str, Any] | None = None) -> SpendReport:
    """Run every check. Findings carry the row number so a human can open that line."""
    rows = [_row_view(r, i) for i, r in enumerate(records, start=2)]
    report = SpendReport(rows_read=len(rows))
    findings: list[Finding] = []

    def add(code: str, severity: str, r: dict[str, Any], amount: Decimal, detail: str) -> None:
        findings.append(Finding(code, severity, r["row"], r["agent_id"], amount, detail,
                                evidence=r["tx_hash"] or f"{r['tool']} @ {r['ts'].isoformat()}"))

    report.total_settled = sum((r["settled"] for r in rows), Decimal("0"))

    # 1. The same charge twice: same receipt, or equal charges within a window.
    seen_tx: dict[str, int] = {}
    for r in rows:
        if r["tx_hash"]:
            if r["tx_hash"] in seen_tx:
                add("duplicate_charge", "error", r, r["settled"],
                    f"same tx_hash as row {seen_tx[r['tx_hash']]}")
            else:
                seen_tx[r["tx_hash"]] = r["row"]
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            same = (a["agent_id"], a["tool"], a["settled"], a["asset"]) == \
                   (b["agent_id"], b["tool"], b["settled"], b["asset"])
            close = abs((b["ts"] - a["ts"]).total_seconds()) <= DUPLICATE_WINDOW_SECONDS
            if same and close and not (a["tx_hash"] and a["tx_hash"] == b["tx_hash"]):
                add("duplicate_charge", "error", b, b["settled"],
                    f"equal charge within {DUPLICATE_WINDOW_SECONDS}s of row {a['row']}")

    # 2. Charged above the authorised maximum.
    for r in rows:
        if r["settled"] > r["quote"] * (1 + ESCALATION_TOLERANCE):
            add("price_escalation", "error", r, r["settled"] - r["quote"],
                f"settled {r['settled']} above quote {r['quote']}")

    # 3. A failed call that still cost money.
    for r in rows:
        if r["status"] in FAILED_STATUSES and r["settled"] > 0:
            add("failed_but_billed", "error", r, r["settled"],
                f"status '{r['status']}' with {r['settled']} charged")

    # 4. A runaway loop: many calls from one agent inside a minute.
    for agent in {r["agent_id"] for r in rows}:
        times = sorted(r["ts"] for r in rows if r["agent_id"] == agent)
        j = 0
        for i, t in enumerate(times):
            while (t - times[j]).total_seconds() > 60:
                j += 1
            if i - j + 1 > RUNAWAY_PER_MINUTE:
                first = next(r for r in rows if r["agent_id"] == agent and r["ts"] == t)
                add("runaway_loop", "warning", first, Decimal("0"),
                    f"{i - j + 1} calls in 60s for {agent} (threshold {RUNAWAY_PER_MINUTE})")
                break

    # 5. Authorised more than used, and nothing came back.
    for r in rows:
        if r["actual"] is not None and r["settled"] > r["actual"] and r["refund"] == 0:
            add("missing_refund", "error", r, r["settled"] - r["actual"],
                f"charged {r['settled']} for actual {r['actual']}, refund not recorded")

    # 6. The same tool and model priced far above its own median: an estimate.
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        if r["model"]:
            groups.setdefault((r["tool"], r["model"]), []).append(r)
    for (_tool, _model), group in groups.items():
        if len(group) < 3:
            continue
        median = Decimal(str(statistics.median(float(g["settled"]) for g in group)))
        if median == 0:
            continue
        for r in group:
            if r["settled"] > median * OVERPAY_MEDIAN_FACTOR:
                add("model_overpay", "warning", r, r["settled"] - median,
                    f"paid {r['settled']} against a median {median} for this tool and model")

    # 7. Money sent to something the record does not identify.
    for r in rows:
        if r["settled"] <= 0:
            continue
        if r["asset"] and r["asset"].upper() not in KNOWN_ASSETS:
            add("unknown_asset", "warning", r, r["settled"], f"asset '{r['asset']}' is not recognised")
        if r["network"] and r["network"].lower() not in KNOWN_NETWORKS:
            add("unknown_network", "warning", r, r["settled"], f"network '{r['network']}' is not recognised")
        if not r["payee"]:
            add("missing_payee", "warning", r, r["settled"], "no payee recorded")

    # 8. A limit that lives only in a prompt is not a limit.
    if not policy:
        findings.append(Finding(
            "budget_bypass", "warning", 0, "-", Decimal("0"),
            "no policy file: any budget lives in a prompt, which the agent can argue with"))
    else:
        spend: dict[str, Decimal] = {}
        for r in rows:
            spend[r["agent_id"]] = spend.get(r["agent_id"], Decimal("0")) + r["settled"]
        for agent, limit_raw in (policy.get("agents") or {}).items():
            limit = _money((limit_raw or {}).get("limit_usd"))
            spent = spend.get(agent, Decimal("0"))
            if limit > 0 and spent > limit:
                findings.append(Finding(
                    "budget_exceeded", "error", 0, agent, spent - limit,
                    f"spent {spent} against a limit of {limit}"))

    report.findings = sorted(findings, key=lambda f: (f.severity != "error", f.row))
    report.estimated_overpay = sum(
        (f.amount for f in report.findings if f.code in {
            "duplicate_charge", "price_escalation", "failed_but_billed",
            "missing_refund", "model_overpay", "budget_exceeded"}),
        Decimal("0"))
    return report
