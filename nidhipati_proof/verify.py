"""Proof of Spend v0.1 verification."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .sign import b64url_decode, verify_signature


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "detail": self.detail}


@dataclass
class ProofResult:
    ok: bool
    receipt_id: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: dict[str, Check] = field(default_factory=dict)
    onchain_verified: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "receipt_id": self.receipt_id,
            "errors": self.errors,
            "warnings": self.warnings,
            "checks": {k: v.as_dict() for k, v in self.checks.items()},
            "onchain_verified": self.onchain_verified,
        }


def load_schema() -> dict[str, Any]:
    return json.loads(files("nidhipati_proof").joinpath("schema.json").read_text(encoding="utf-8"))


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _public_key_bytes(public_key: bytes | str) -> bytes:
    if isinstance(public_key, bytes):
        return public_key
    text = public_key.strip()
    if text.startswith("0x") or all(c in "0123456789abcdefABCDEF" for c in text):
        return bytes.fromhex(text[2:] if text.startswith("0x") else text)
    return b64url_decode(text)


def verify_document(
    document: dict[str, Any],
    public_key: bytes | str,
    now: datetime | None = None,
) -> ProofResult:
    result = ProofResult(ok=False, receipt_id=str(document.get("receipt_id", "")))
    validator = Draft202012Validator(load_schema(), format_checker=FormatChecker())
    schema_errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    result.checks["schema"] = Check("schema", not schema_errors, "; ".join(e.message for e in schema_errors[:5]))
    if schema_errors:
        result.errors.extend(f"schema: {e.message}" for e in schema_errors[:10])

    try:
        key = _public_key_bytes(public_key)
    except Exception as exc:
        result.checks["signature"] = Check("signature", False, f"bad public key: {exc}")
        result.errors.append("signature: bad public key")
        return result

    sig = document.get("signature") or {}
    alg_ok = sig.get("alg") == "Ed25519"
    result.checks["signature_alg"] = Check("signature_alg", alg_ok, str(sig.get("alg")))
    if not alg_ok:
        result.errors.append("signature_alg: expected Ed25519")

    sig_ok = verify_signature(document, key)
    result.checks["signature"] = Check("signature", sig_ok, "Ed25519" if sig_ok else "invalid")
    if not sig_ok:
        result.errors.append("signature: invalid")

    payment = document.get("payment") or {}
    mandate = document.get("mandate") or {}
    settled = _parse_time(payment.get("settled_at"))
    expires = _parse_time(mandate.get("expires_at"))
    expiry_ok = bool(settled and expires and settled <= expires)
    result.checks["mandate_expiry"] = Check("mandate_expiry", expiry_ok, "settled <= expires")
    if not expiry_ok:
        result.errors.append("mandate_expiry: payment after mandate expiry or bad date")

    amount = _decimal(payment.get("amount"))
    amount_ok = amount is not None and amount > 0
    result.checks["amount_positive"] = Check("amount_positive", amount_ok, str(payment.get("amount")))
    if not amount_ok:
        result.errors.append("amount: must be positive")

    usage = document.get("usage") or {}
    qty = _decimal(usage.get("quantity"))
    unit = _decimal(usage.get("unit_price"))
    usage_ok = bool(qty is not None and unit is not None and amount is not None and abs(qty * unit - amount) <= Decimal("0.000000001"))
    result.checks["usage_amount"] = Check("usage_amount", usage_ok, "quantity * unit_price == amount")
    if not usage_ok:
        result.errors.append("usage: quantity * unit_price does not match payment amount")

    refund = document.get("refund") or {}
    refund_amount = _decimal(refund.get("amount", "0")) or Decimal("0")
    refund_ok = amount is not None and refund_amount >= 0 and refund_amount <= amount
    result.checks["refund"] = Check("refund", refund_ok, "0 <= refund <= amount")
    if not refund_ok:
        result.errors.append("refund: must be between 0 and payment amount")

    verdict = document.get("verdict") or {}
    verdict_ok = verdict.get("decision") == "allow"
    result.checks["verdict_allow"] = Check("verdict_allow", verdict_ok, str(verdict.get("decision")))
    if not verdict_ok:
        result.errors.append("verdict: settled payment requires decision=allow")

    receipt_ok = bool(str(document.get("receipt_id", "")).strip())
    result.checks["receipt_id"] = Check("receipt_id", receipt_ok, "non-empty")
    if not receipt_ok:
        result.errors.append("receipt_id: empty")

    result.warnings.append("onchain_verified=false: v0.1 does not query the chain")
    result.ok = not result.errors
    return result
