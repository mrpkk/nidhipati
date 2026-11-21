"""Возврат в кассе: статус refunded с доказательством, и только владельцем.

21.11.2026: статус `refunded` был в модели, но ни одна ручка его не ставила —
возврат существовал как слово. Здесь: токен владельца, обязательное доказательство
(хеш USDC или ссылка возврата карты), идемпотентность и запись события.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def api(tmp_path, monkeypatch):
    from nidhipati_proof.payment_hub import web as payweb

    monkeypatch.setenv("NIDHIPATI_PAYMENT_DB", str(tmp_path / "pay.db"))
    monkeypatch.setenv("NIDHIPATI_PAYOUT_ADDRESS", "0x" + "ab" * 20)
    monkeypatch.setenv("NIDHIPATI_ADMIN_TOKEN", "s3cret-admin")
    payweb._STORE = None  # type: ignore[attr-defined]

    def call(method: str, url: str, payload: dict | None = None, headers: dict | None = None):
        body = json.dumps(payload).encode() if payload is not None else None
        base = {"Content-Type": "application/json", **(headers or {})}
        return payweb.handle_pay_request(method, url, base, body)

    code, order, _ = call("POST", "/pay/create", {
        "order_id": "ord-refund", "amount_fiat": "19", "currency": "USD",
        "product_id": "crypto-mcp-month", "customer_email": "buyer@example.com"})
    assert code == 200, order
    return call, order


def test_refund_requires_admin_token(api):
    call, _ = api
    code, body, _ = call("POST", "/pay/refund", {"order_id": "ord-refund", "reason": "late"})
    assert code == 403 and body["error"] == "admin_token_required"


def test_refund_requires_evidence(api):
    call, _ = api
    code, body, _ = call("POST", "/pay/refund",
                         {"order_id": "ord-refund", "reason": "не доставлено вовремя"},
                         {"X-Nidhipati-Admin": "s3cret-admin"})
    assert code == 400 and body["error"] == "evidence_required"


def test_refund_marks_order_and_keeps_the_hash(api):
    call, _ = api
    code, body, _ = call("POST", "/pay/refund",
                         {"order_id": "ord-refund", "reason": "не доставлено вовремя",
                          "tx_hash": "0xrefund"},
                         {"X-Nidhipati-Admin": "s3cret-admin"})
    assert code == 200 and body["ok"] is True
    order = body["order"]
    assert order["status"] == "refunded"
    assert order["meta"]["refund_tx_hash"] == "0xrefund"
    assert "не доставлено" in order["meta"]["refund_reason"]

    # страница заказа отдаёт тот же статус — возврат виден покупателю
    got, page, _ = call("GET", "/pay/order/ord-refund")
    assert got == 200 and page["order"]["status"] == "refunded"


def test_card_refund_accepts_provider_reference(api):
    call, _ = api
    code, body, _ = call("POST", "/pay/refund",
                         {"order_id": "ord-refund", "reason": "provider refund",
                          "refund_ref": "paygate-rf-1"},
                         {"X-Nidhipati-Admin": "s3cret-admin"})
    assert code == 200 and body["order"]["meta"]["refund_ref"] == "paygate-rf-1"


def test_second_refund_is_idempotent(api):
    call, _ = api
    headers = {"X-Nidhipati-Admin": "s3cret-admin"}
    call("POST", "/pay/refund", {"order_id": "ord-refund", "reason": "late", "tx_hash": "0xa"}, headers)
    code, body, _ = call("POST", "/pay/refund",
                         {"order_id": "ord-refund", "reason": "late again", "tx_hash": "0xb"}, headers)
    assert code == 200 and body["duplicate"] is True


def test_unknown_order_is_404(api):
    call, _ = api
    code, body, _ = call("POST", "/pay/refund",
                         {"order_id": "nope", "reason": "x", "tx_hash": "0x"},
                         {"X-Nidhipati-Admin": "s3cret-admin"})
    assert code == 404 and body["error"] == "not_found"


def test_no_admin_token_configured_means_closed(api, monkeypatch):
    call, _ = api
    monkeypatch.delenv("NIDHIPATI_ADMIN_TOKEN", raising=False)
    code, _, _ = call("POST", "/pay/refund", {"order_id": "ord-refund", "reason": "x",
                                              "tx_hash": "0x"},
                      {"X-Nidhipati-Admin": "s3cret-admin"})
    assert code == 403


def test_runbook_names_both_rails_and_the_evidence():
    """Инструкция должна говорить про оба рельса и доказательства, иначе вернут «на слово»."""
    doc = (ROOT / "docs" / "REFUND.md").read_text(encoding="utf-8")
    for needle in ("X-Nidhipati-Admin", "tx_hash", "refund_ref", "тот же адрес",
                   "PROGRESS.md", "progress.py", "duplicate"):
        assert needle in doc, needle
    assert "карт" in doc.lower() and "USDC" in doc


# ── письмо покупателю и реестр возвратов ──────────────────────────────────

@pytest.fixture()
def mailed(api, monkeypatch):
    """Перехватываем отправку: тест не должен ходить в SMTP."""
    call, _ = api
    sent: list[tuple[str, str, str]] = []

    def fake_send(*args, **kwargs):
        # возможны две сигнатуры: (row) и (to, order, reason, evidence)
        if args and isinstance(args[0], dict):
            sent.append(("row", args[0].get("stage", ""), ""))
            return (True, "")
        if len(args) >= 4:
            sent.append((args[0], args[2], args[3]))
            return ""
        return ""

    from nidhipati_proof.payment_hub import intake

    monkeypatch.setattr(intake, "_send", lambda to, subject, body: (sent.append((to, subject, body)), "")[1])
    return call, sent


def test_refund_emails_the_buyer(mailed):
    call, sent = mailed
    code, body, _ = call("POST", "/pay/refund",
                         {"order_id": "ord-refund", "reason": "не доставлено вовремя",
                          "tx_hash": "0xrefund"},
                         {"X-Nidhipati-Admin": "s3cret-admin"})
    assert code == 200 and body["refund_email"] == "sent"
    assert sent, "письмо о возврате не отправлено"
    to, subject, text = sent[-1]
    assert "buyer@example.com" in to
    assert "возврат" in subject.lower()
    assert "0xrefund" in text and "не доставлено" in text


def test_refund_records_email_failure_honestly(mailed, monkeypatch):
    call, _sent = mailed
    from nidhipati_proof.payment_hub import intake

    monkeypatch.setattr(intake, "_send", lambda to, subject, body: "SMTP is not configured")
    code, body, _ = call("POST", "/pay/refund",
                         {"order_id": "ord-refund", "reason": "late", "tx_hash": "0x1"},
                         {"X-Nidhipati-Admin": "s3cret-admin"})
    assert code == 200 and "SMTP" in body["refund_email"]


def test_refunds_registry_requires_token(api):
    call, _ = api
    code, body, _ = call("GET", "/pay/refunds")
    assert code == 403 and body["error"] == "admin_token_required"


def test_refunds_registry_lists_what_was_returned(mailed):
    call, _ = mailed
    headers = {"X-Nidhipati-Admin": "s3cret-admin"}
    call("POST", "/pay/refund", {"order_id": "ord-refund", "reason": "не доставлено",
                                 "tx_hash": "0xabc"}, headers)
    code, body, _ = call("GET", "/pay/refunds", None, headers)
    assert code == 200
    assert body["count"] == 1
    row = body["refunds"][0]
    assert row["order_id"] == "ord-refund" and row["evidence"] == "0xabc"
    assert row["reason"].startswith("не доставлено")
    assert body["total_fiat"] == 19.0


def test_runbook_mentions_email_and_registry():
    doc = (ROOT / "docs" / "REFUND.md").read_text(encoding="utf-8")
    assert "/pay/refunds" in doc and "refund_email" in doc
    assert "X-Nidhipati-Admin" in doc
