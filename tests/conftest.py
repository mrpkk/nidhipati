"""Общие настройки тестов Nidhipati.

Главное здесь — почта. Тесты оплаты вызывают `notify_owner` и `send_intake`,
а те отправляют письма по-настоящему: без заглушки прогон тестов рассылает
письма владельцу и покупателям (12.11.2026 — прогон отправил четыре письма
на maxim.pkk@gmail.com). Заглушка ставится на весь модуль, автоматически, для
всех тестов: письмо собирается, но не уходит.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_real_mail(monkeypatch):
    """Ни один тест не отправляет настоящую почту."""
    from nidhipati_proof.payment_hub import intake

    sent: list[tuple[str, str, str]] = []

    def fake_send(to: str, subject: str, body: str) -> str:
        sent.append((to, subject, body))
        return ""

    monkeypatch.setattr(intake, "_send", fake_send)
    return sent
