"""Reserve and NAV report for a tokenised asset.

Why: an issuer says "fully backed" and shows a PDF. A holder cannot multiply that
PDF by anything. This turns the issuer's own numbers into a NAV with explicit
formulas, per-line evidence hashes, and a refusal to call a reserve backed when a
line has no price.

Honest boundary: nothing here is verified on-chain or with a custodian. The tool
checks the arithmetic and the *presence* of sources, and says plainly that it is
not a statutory audit.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes

DISCLAIMER = (
    "Not a statutory audit. The numbers come from the issuer's own inputs; no balance "
    "was confirmed with a custodian and nothing was read from chain in v0.3. Verify each "
    "source hash before relying on this report."
)
MAX_PRICE_AGE_DAYS = 3


@dataclass
class Line:
    asset: str
    kind: str
    quantity: Decimal
    price: Decimal | None
    haircut: Decimal
    source: str
    price_as_of: datetime | None = None
    custodian: str = ""
    issues: list[str] = field(default_factory=list)

    @property
    def priced(self) -> bool:
        return self.price is not None

    @property
    def value(self) -> Decimal:
        """quantity × price × (1 − haircut). No price means no value, not a guess."""
        if self.price is None:
            return Decimal("0")
        return self.quantity * self.price * (Decimal("1") - self.haircut)

    def evidence(self) -> str:
        payload = {
            "asset": self.asset, "kind": self.kind, "quantity": str(self.quantity),
            "price": None if self.price is None else str(self.price),
            "haircut": str(self.haircut), "source": self.source,
            "price_as_of": self.price_as_of.isoformat() if self.price_as_of else None,
        }
        return "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset, "kind": self.kind,
            "quantity": str(self.quantity),
            "price": None if self.price is None else str(self.price),
            "haircut": str(self.haircut),
            "value": str(self.value.quantize(Decimal("0.01"))),
            "source": self.source,
            "custodian": self.custodian,
            "price_as_of": self.price_as_of.isoformat() if self.price_as_of else None,
            "evidence": self.evidence(),
            "issues": self.issues,
        }


@dataclass
class ReserveReport:
    issuer: str = ""
    token: str = ""
    as_of: datetime | None = None
    supply: Decimal | None = None
    reserve_lines: list[Line] = field(default_factory=list)
    liability_lines: list[Line] = field(default_factory=list)
    findings: list[dict[str, str]] = field(default_factory=list)
    statement_declared: str = ""
    statement_computed: str = ""
    disclaimer: str = DISCLAIMER

    @property
    def nav(self) -> Decimal | None:
        if self.supply is None:
            return None
        gross = sum((l.value for l in self.reserve_lines), Decimal("0"))
        liabilities = sum((l.value for l in self.liability_lines), Decimal("0"))
        return gross - liabilities

    @property
    def unpriced_lines(self) -> list[Line]:
        return [l for l in self.reserve_lines if not l.priced]

    @property
    def nav_complete(self) -> bool:
        return not self.unpriced_lines and self.supply is not None

    @property
    def backing_ratio(self) -> Decimal | None:
        """Refused, not guessed: a ratio over an incomplete reserve is a lie."""
        nav = self.nav
        if not self.nav_complete or not self.supply:
            return None
        return (nav / self.supply).quantize(Decimal("0.0001"))

    @property
    def verdict(self) -> str:
        if not self.nav_complete:
            return "incomplete"
        ratio = self.backing_ratio or Decimal("0")
        return "backed" if ratio >= 1 else "underbacked"

    def add(self, code: str, severity: str, detail: str, line: str = "") -> None:
        self.findings.append({"code": code, "severity": severity, "line": line, "detail": detail})

    def errors(self) -> list[dict[str, str]]:
        return [f for f in self.findings if f["severity"] == "error"]

    def as_dict(self) -> dict[str, Any]:
        return {
            "issuer": self.issuer,
            "token": self.token,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "supply": None if self.supply is None else str(self.supply),
            "nav": None if self.nav is None else str(self.nav.quantize(Decimal("0.01"))),
            "backing_ratio": None if self.backing_ratio is None else str(self.backing_ratio),
            "nav_complete": self.nav_complete,
            "verdict": self.verdict,
            "reserve": [l.as_dict() for l in self.reserve_lines],
            "liabilities": [l.as_dict() for l in self.liability_lines],
            "statement": {
                "declared": self.statement_declared,
                "computed": self.statement_computed,
            },
            "findings": self.findings,
            "disclaimer": self.disclaimer,
        }

    def to_markdown(self) -> str:
        nav = "—" if self.nav is None else f"{self.nav.quantize(Decimal('0.01'))}"
        ratio = "—" if self.backing_ratio is None else str(self.backing_ratio)
        lines = [
            "# Reserve and NAV report",
            "",
            f"**Issuer:** {self.issuer}  ",
            f"**Token:** {self.token}  ",
            f"**As of:** {self.as_of.isoformat() if self.as_of else '—'}  ",
            f"**Supply:** {self.supply if self.supply is not None else '—'}  ",
            f"**NAV:** {nav}  ",
            f"**Backing ratio:** {ratio}  ",
            f"**Verdict:** **{self.verdict}**",
            "",
            "## Reserve composition",
            "",
            "| Asset | Kind | Quantity | Price | Haircut | Value | Source | Evidence |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for l in self.reserve_lines:
            price = "—" if l.price is None else str(l.price)
            lines.append(
                f"| {l.asset} | {l.kind} | {l.quantity} | {price} | {l.haircut} | "
                f"{l.value.quantize(Decimal('0.01'))} | {l.source or '—'} | `{l.evidence()}` |")
        if self.liability_lines:
            lines += ["", "## Liabilities", "",
                      "| Item | Quantity | Price | Value | Source |",
                      "|---|---|---|---|---|"]
            for l in self.liability_lines:
                lines.append(f"| {l.asset} | {l.quantity} | {l.price} | "
                             f"{l.value.quantize(Decimal('0.01'))} | {l.source or '—'} |")
        lines += ["", "## Findings", ""]
        if not self.findings:
            lines += ["No finding: every line carried a price and a source, and the reserve "
                      "covered the supply at the stated date.", ""]
        else:
            lines += ["| Severity | Code | Line | Detail |", "|---|---|---|---|"]
            for f in self.findings:
                lines.append(f"| {f['severity']} | `{f['code']}` | {f['line'] or '—'} | {f['detail']} |")
            lines.append("")
        if self.statement_declared:
            ok = self.statement_declared == self.statement_computed
            lines += ["", f"Custodian statement hash: `{self.statement_declared}` — "
                          f"{'matches the file' if ok else 'does not match the file'}"]
        lines += ["", f"> {self.disclaimer}", ""]
        return "\n".join(lines)


def _dec(value: Any, what: str) -> Decimal:
    if value is None or str(value).strip() == "":
        raise ValueError(f"{what} is required")
    try:
        return Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError(f"{what} is not a number: {value!r}") from exc


def _opt_dec(value: Any) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    return Decimal(str(value).strip())


def _ts(value: Any) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _line(raw: dict[str, Any], report: ReserveReport, is_liability: bool) -> Line:
    name = str(raw.get("asset") or "").strip()
    if not name:
        raise ValueError("every line needs an 'asset'")
    haircut = _opt_dec(raw.get("haircut")) or Decimal("0")
    line = Line(
        asset=name,
        kind=str(raw.get("kind") or ("liability" if is_liability else "other")).strip(),
        quantity=_dec(raw.get("quantity"), f"{name}: quantity"),
        price=_opt_dec(raw.get("price")),
        haircut=haircut,
        source=str(raw.get("source") or "").strip(),
        price_as_of=_ts(raw.get("price_as_of")),
        custodian=str(raw.get("custodian") or "").strip(),
    )
    if not is_liability:
        if line.price is None:
            line.issues.append("no price: excluded from NAV, backing ratio refused")
            report.add("unpriced", "error",
                       f"{name}: no price, so no value can be computed", name)
        if not line.source:
            line.issues.append("no source")
            report.add("missing_source", "error", f"{name}: no source for the quantity", name)
        if haircut < 0 or haircut >= 1:
            line.issues.append("haircut out of range")
            report.add("haircut_out_of_range", "error",
                       f"{name}: haircut {haircut} is outside [0, 1)", name)
        if line.price_as_of and report.as_of:
            age = (report.as_of - line.price_as_of).days
            if age > MAX_PRICE_AGE_DAYS:
                line.issues.append(f"price {age} days old")
                report.add("stale_price", "warning",
                           f"{name}: price dated {line.price_as_of.date()}, {age} days before "
                           f"the report date", name)
    return line


def load_reserve(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ValueError(f"no such file: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("the reserve input must be a JSON object")
    return data


def build_report(data: dict[str, Any], base_dir: str | Path | None = None) -> ReserveReport:
    """Turn the issuer's inputs into a report. Missing data is marked, never filled."""
    report = ReserveReport(
        issuer=str(data.get("issuer") or "").strip(),
        token=str(data.get("token") or data.get("symbol") or "").strip(),
        as_of=_ts(data.get("as_of")),
    )
    if report.as_of is None:
        raise ValueError("'as_of' is required: a NAV without a date is not a NAV")
    supply_raw = data.get("supply")
    if isinstance(supply_raw, dict):
        supply_raw = supply_raw.get("value")
    report.supply = _opt_dec(supply_raw)
    if not report.supply:
        report.add("missing_supply", "error", "no token supply given: backing cannot be judged")

    for raw in data.get("reserve") or []:
        report.reserve_lines.append(_line(raw, report, is_liability=False))
    for raw in data.get("liabilities") or []:
        report.liability_lines.append(_line(raw, report, is_liability=True))

    if not report.reserve_lines:
        report.add("empty_reserve", "error", "the reserve has no lines")

    seen: dict[str, int] = {}
    for l in report.reserve_lines:
        seen[l.asset] = seen.get(l.asset, 0) + 1
    for asset, count in seen.items():
        if count > 1:
            report.add("duplicate_asset", "warning",
                       f"{asset} appears {count} times: check it is not counted twice", asset)

    statement = data.get("statement") or {}
    declared = str(statement.get("hash") or "").strip()
    if declared:
        report.statement_declared = declared
        path_raw = statement.get("path")
        if path_raw:
            sp = Path(path_raw)
            if not sp.is_absolute() and base_dir is not None:
                sp = Path(base_dir) / sp
            if sp.exists():
                digest = hashlib.sha256(sp.read_bytes()).hexdigest()
                report.statement_computed = declared.split(":")[-1] if declared.startswith("sha256:") \
                    else digest
                if report.statement_computed != digest:
                    report.add("statement_hash_mismatch", "error",
                               "the declared statement hash does not match the file provided")
            else:
                report.add("statement_missing", "warning",
                           f"statement file not found: {sp}")
        else:
            report.add("statement_unchecked", "warning",
                       "a statement hash was given without the file: presence of the document "
                       "was not checked")

    if report.nav_complete and report.backing_ratio is not None and report.backing_ratio < 1:
        report.add("underbacked", "error",
                   f"reserve covers {report.backing_ratio} of the supply")
    return report
