"""Письма после оплаты: покупателю — форма заявки, владельцу — уведомление.

Проверяется то, что важно: письмо действительно уходит на адрес из заказа,
в письме есть сумма и хеш, а сломанная почта не выглядит как «всё хорошо».
"""
from __future__ import annotations

import pytest

from nidhipati_proof.payment_hub import intake


@pytest.fixture()
def sent(monkeypatch):
    """Все письма собираются в список вместо отправки.

    Заглушка ставится и в conftest (для всех тестов), но здесь — явно:
    тест про письма должен видеть именно свои письма.
    """
    box: list[tuple[str, str, str]] = []

    def fake_send(to: str, subject: str, body: str) -> str:
        box.append((to, subject, body))
        return ""

    monkeypatch.setattr(intake, "_send", fake_send)
    return box


def test_valid_email():
    assert intake.valid_email("buyer@example.com")
    assert not intake.valid_email("buyer@example")
    assert not intake.valid_email("")
    assert not intake.valid_email("a b@example.com")


def test_intake_email_carries_amount_and_tx(sent):
    order = {"order_id": "o1", "amount_fiat": "500", "currency": "USD",
             "txid_in": "0x" + "ab" * 32, "product_id": "agent-spend-audit"}
    assert intake.send_intake("buyer@example.com", order=order) == ""
    assert len(sent) == 1
    to, subject, body = sent[0]
    assert to == "buyer@example.com"
    assert "500" in subject or "500" in body
    assert "0x" + "ab" * 32 in body
    # Все пять вопросов формы на месте — без них работа не начинается.
    for question, _hint in intake.SPEND_AUDIT_QUESTIONS:
        assert question in body


def test_intake_is_not_sent_without_email(sent):
    order = {"order_id": "o1", "amount_fiat": "500", "currency": "USD"}
    assert intake.send_intake("", order=order) != ""
    assert sent == []


def test_broken_mail_is_reported_not_swallowed(sent, monkeypatch):
    monkeypatch.setattr(intake, "_send",
                        lambda to, subject, body: "SMTP is not configured")
    order = {"order_id": "o1", "amount_fiat": "500", "currency": "USD"}
    assert intake.send_intake("buyer@example.com", order=order) == "SMTP is not configured"


def test_owner_is_notified_about_paid_order(sent):
    order = {"order_id": "o1", "amount_fiat": "500", "currency": "USD",
             "txid_in": "0x" + "cd" * 32, "product_id": "agent-spend-audit",
             "status": "fulfilled"}
    assert intake.notify_owner(order=order) == ""
    assert len(sent) == 1
    to, subject, body = sent[0]
    assert to == intake.OWNER_EMAIL
    assert "o1" in subject
    assert "500" in body
