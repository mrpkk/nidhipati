"""Resolution evidence for a prediction market.

Why: a market resolves, someone disagrees, and the argument is settled by whoever
shouts last. This checks whether the declared outcome is supported by the sources
the resolver actually read, whether those sources conflict, and whether each claim
carries a quote and a hash.

Honest boundary: nothing here places a trade or reads a market contract. The tool
weighs the documents you provide and states what they can and cannot support.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes

DISCLAIMER = (
    "Not a statutory audit and not trading. No market was read on-chain and no position "
    "was taken in v0.4. The report weighs the sources provided; a source that is missing "
    "cannot be missed."
)
OUTCOMES = {"YES", "NO", "INVALID", "VOID"}
MIN_INDEPENDENT_SOURCES = 2


@dataclass
class Source:
    name: str
    claim: str
    quote: str = ""
    url: str = ""
    retrieved_at: datetime | None = None
    declared_hash: str = ""

    def evidence(self) -> str:
        payload = {"name": self.name, "claim": self.claim, "quote": self.quote,
                   "url": self.url,
                   "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None}
        return "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "claim": self.claim, "quote": self.quote, "url": self.url,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
            "declared_hash": self.declared_hash, "evidence": self.evidence(),
        }


@dataclass
class ResolveReport:
    market_id: str = ""
    question: str = ""
    rules_url: str = ""
    rules_hash: str = ""
    rules_computed: str = ""
    deadline: datetime | None = None
    declared_outcome: str = ""
    declared_at: datetime | None = None
    declared_by: str = ""
    sources: list[Source] = field(default_factory=list)
    findings: list[dict[str, str]] = field(default_factory=list)
    disclaimer: str = DISCLAIMER

    def add(self, code: str, severity: str, detail: str, source: str = "") -> None:
        self.findings.append({"code": code, "severity": severity, "source": source, "detail": detail})

    def errors(self) -> list[dict[str, str]]:
        return [f for f in self.findings if f["severity"] == "error"]

    @property
    def agreeing(self) -> list[Source]:
        return [s for s in self.sources if s.claim == self.declared_outcome]

    @property
    def contradicting(self) -> list[Source]:
        return [s for s in self.sources if s.claim and s.claim != self.declared_outcome]

    @property
    def verdict(self) -> str:
        if not self.sources:
            return "insufficient"
        if any(f["code"] in {"missing_evidence", "unknown_outcome"} for f in self.findings):
            return "insufficient"
        if self.contradicting:
            return "disputed"
        if len(self.agreeing) < MIN_INDEPENDENT_SOURCES:
            return "single_source"
        return "supported"

    def as_dict(self) -> dict[str, Any]:
        return {
            "market_id": self.market_id,
            "question": self.question,
            "rules": {"url": self.rules_url, "declared_hash": self.rules_hash,
                      "computed_hash": self.rules_computed},
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "declared": {"outcome": self.declared_outcome,
                         "at": self.declared_at.isoformat() if self.declared_at else None,
                         "by": self.declared_by},
            "sources": [s.as_dict() for s in self.sources],
            "agreeing": len(self.agreeing),
            "contradicting": len(self.contradicting),
            "verdict": self.verdict,
            "findings": self.findings,
            "disclaimer": self.disclaimer,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Resolution evidence report",
            "",
            f"**Market:** {self.market_id} — {self.question}  ",
            f"**Rules:** {self.rules_url or '—'}  ",
            f"**Deadline:** {self.deadline.isoformat() if self.deadline else '—'}  ",
            f"**Declared outcome:** **{self.declared_outcome or '—'}** by {self.declared_by or '—'} "
            f"at {self.declared_at.isoformat() if self.declared_at else '—'}  ",
            f"**Verdict:** **{self.verdict}** ({len(self.agreeing)} agreeing, "
            f"{len(self.contradicting)} contradicting)",
            "",
            "## Sources",
            "",
            "| Source | Claim | Retrieved | Quote | Evidence |",
            "|---|---|---|---|---|",
        ]
        for s in self.sources:
            quote = (s.quote or "—").replace("\n", " ")
            lines.append(f"| {s.name} | {s.claim or '—'} | "
                         f"{s.retrieved_at.date() if s.retrieved_at else '—'} | {quote} | "
                         f"`{s.evidence()}` |")
        lines += ["", "## Findings", ""]
        if not self.findings:
            lines += ["No finding: every source agrees with the declared outcome and carries a "
                      "quote and a hash.", ""]
        else:
            lines += ["| Severity | Code | Source | Detail |", "|---|---|---|---|"]
            for f in self.findings:
                lines.append(f"| {f['severity']} | `{f['code']}` | {f['source'] or '—'} | {f['detail']} |")
            lines.append("")
        lines += [f"> {self.disclaimer}", ""]
        return "\n".join(lines)


def _ts(value: Any, what: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{what} is not ISO-8601: {value!r}") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_market(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ValueError(f"no such file: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("the market input must be a JSON object")
    return data


def build_report(data: dict[str, Any], base_dir: str | Path | None = None) -> ResolveReport:
    declared = data.get("declared") or {}
    report = ResolveReport(
        market_id=str(data.get("market_id") or "").strip(),
        question=str(data.get("question") or "").strip(),
        rules_url=str(data.get("rules_url") or "").strip(),
        rules_hash=str(data.get("rules_hash") or "").strip(),
        deadline=_ts(data.get("deadline"), "deadline"),
        declared_outcome=str(declared.get("outcome") or "").strip().upper(),
        declared_at=_ts(declared.get("at"), "declared.at"),
        declared_by=str(declared.get("by") or "").strip(),
    )
    if not report.market_id:
        raise ValueError("'market_id' is required")
    if not report.declared_outcome:
        raise ValueError("'declared.outcome' is required")
    if not report.declared_at:
        raise ValueError("'declared.at' is required: an outcome without a time cannot be checked")
    if report.declared_outcome not in OUTCOMES:
        report.add("unknown_outcome", "error",
                   f"outcome '{report.declared_outcome}' is not one of {sorted(OUTCOMES)}")

    if report.deadline and report.declared_at and report.declared_at < report.deadline:
        report.add("premature_resolution", "warning",
                   f"declared at {report.declared_at.isoformat()}, before the deadline "
                   f"{report.deadline.isoformat()}")

    rules = data.get("rules") or {}
    rules_path = rules.get("path")
    if report.rules_hash and rules_path:
        rp = Path(rules_path)
        if not rp.is_absolute() and base_dir is not None:
            rp = Path(base_dir) / rp
        if rp.exists():
            digest = hashlib.sha256(rp.read_bytes()).hexdigest()
            report.rules_computed = digest
            declared_digest = report.rules_hash.split(":")[-1]
            if declared_digest != digest:
                report.add("rules_hash_mismatch", "error",
                           "the declared rules hash does not match the rules file")
        else:
            report.add("rules_file_missing", "warning", f"rules file not found: {rp}")
    elif report.rules_hash:
        report.add("rules_unchecked", "warning",
                   "rules hash given without the file: the rules text was not checked")

    for raw in data.get("sources") or []:
        name = str(raw.get("name") or "").strip()
        if not name:
            raise ValueError("every source needs a 'name'")
        src = Source(
            name=name,
            claim=str(raw.get("claim") or "").strip().upper(),
            quote=str(raw.get("quote") or "").strip(),
            url=str(raw.get("url") or "").strip(),
            retrieved_at=_ts(raw.get("retrieved_at"), f"{name}: retrieved_at"),
            declared_hash=str(raw.get("hash") or "").strip(),
        )
        report.sources.append(src)
        if not src.quote:
            report.add("missing_evidence", "error",
                       f"{name}: no quote, so the claim cannot be checked against the text", name)
        if src.claim and src.claim not in OUTCOMES:
            report.add("unknown_source_claim", "warning",
                       f"{name}: claim '{src.claim}' is not a market outcome", name)
        if src.retrieved_at and report.deadline and src.retrieved_at < report.deadline:
            report.add("pre_deadline_source", "warning",
                       f"{name}: retrieved before the deadline — it cannot settle the question", name)

    if not report.sources:
        report.add("no_sources", "error", "no source was provided: nothing supports the outcome")

    claims = {s.claim for s in report.sources if s.claim}
    if len(claims) > 1:
        report.add("sources_conflict", "error",
                   f"sources disagree: {', '.join(sorted(claims))}")
    elif claims and report.declared_outcome not in claims:
        report.add("source_contradicts", "error",
                   f"every source says {', '.join(sorted(claims))} against the declared "
                   f"{report.declared_outcome}")

    if len({s.quote or s.url or s.name for s in report.sources}) < MIN_INDEPENDENT_SOURCES \
            and report.sources:
        report.add("single_source", "warning",
                   f"fewer than {MIN_INDEPENDENT_SOURCES} independent sources: one document is "
                   f"not a settlement")
    return report
