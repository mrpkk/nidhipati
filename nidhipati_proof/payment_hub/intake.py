"""Письмо после оплаты: форма заявки покупателю и уведомление владельцу.

Зачем. Витрина обещает «intake form по email». Обещание без письма — это
обещание, которое человек ждёт и не получает: деньги пришли, а ответа нет.
Поэтому письмо отправляется здесь же, в момент подтверждения оплаты.

Что честно в письме: сумма и хеш — из цепи, адрес — из конфигурации. Никаких
«ваш заказ принят, мы свяжемся»: письмо содержит вопросы, без ответов на них
работа не начинается.

Письмо не отправляется — это не отказ оплаты. Оплата уже подтверждена, заказ
записан, квитанция собрана. В ответе покупателю честно сказано, что письмо не
ушло и что делать вместо этого (написать владельцу, указав хеш).
"""
from __future__ import annotations

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Any

#: Куда писать владельцу о новой оплате. Адрес публичный (он же на страницах).
OWNER_EMAIL = os.environ.get("NIDHIPATI_OWNER_EMAIL", "maxim.pkk@gmail.com")

#: Вопросы формы заявки для аудита расходов. Ровно то, без чего работа не идёт.
SPEND_AUDIT_QUESTIONS = (
    ("Company / product", "name and public URL if it has one"),
    ("Period", "which month the export covers"),
    ("Providers", "which models, APIs or payment rails appear in the export"),
    ("Format", "CSV or JSON, and the column names if they are unusual"),
    ("What looks wrong", "duplicates, price changes, failed calls, refunds, "
                        "unknown charges — or 'not sure, that is what I want to know'"),
)


def _env_file() -> dict[str, str]:
    """EMAIL и MYACCOUNT_GOOGLE из ~/.env.

    Пароль почты в unit-файле systemd — худшее место для секрета: он виден в
    `systemctl cat` и в каждом дампе. Поэтому читаем файл, а не окружение.
    """
    env: dict[str, str] = {}
    try:
        text = (Path.home() / ".env").read_text(encoding="utf-8")
    except OSError:
        return {}
    for line in text.splitlines():
        m = re.match(r'^([A-Z0-9_]+)=["\']?(.*?)["\']?$', line)
        if m:
            env[m.group(1)] = m.group(2)
    return env


def mail_credentials() -> tuple[str, str]:
    env = _env_file()
    return env.get("EMAIL", ""), env.get("MYACCOUNT_GOOGLE", "").replace(" ", "")


def valid_email(value: str) -> bool:
    value = (value or "").strip()
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))


def _send(to: str, subject: str, body: str) -> str:
    """Отправить письмо. "" — успех, иначе причина."""
    sender, password = mail_credentials()
    if not sender or not password:
        return "SMTP is not configured (no EMAIL or MYACCOUNT_GOOGLE in ~/.env)"
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465,
                              context=ssl.create_default_context(), timeout=20) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)
        return ""
    except Exception as exc:  # noqa: BLE001 — причина нужна, а не класс ошибки
        return f"{type(exc).__name__}: {exc}"


def intake_body(*, order: dict[str, Any], evidence: dict[str, Any] | None) -> str:
    """Текст письма покупателю: подтверждение и вопросы."""
    amount = order.get("amount_fiat", "")
    currency = order.get("currency", "USD")
    tx = order.get("txid_in") or "—"
    order_id = order.get("order_id", "")
    lines = [
        f"Hi,",
        "",
        f"Payment received: {amount} {currency} for order {order_id}.",
        f"Transaction: {tx}",
        "",
        "To start the audit, answer these five questions and attach the export:",
        "",
    ]
    for i, (question, hint) in enumerate(SPEND_AUDIT_QUESTIONS, 1):
        lines.append(f"{i}. {question} — {hint}")
    lines += [
        "",
        "Send the export as CSV or JSON. No keys, no seed phrases, no customer data.",
        "",
        "Scope: one month, one export, one named owner. The report takes five working",
        "days from complete data. If the records show no leaks, the report says so.",
        "",
        "Maksim",
    ]
    return "\n".join(lines)


def send_intake(to: str, *, order: dict[str, Any],
                evidence: dict[str, Any] | None = None) -> str:
    """Отправить покупателю форму заявки. "" — успех, иначе причина."""
    if not valid_email(to):
        return "no valid email for the intake form"
    return _send(to, "Nidhipati audit — payment received, intake form inside",
                 intake_body(order=order, evidence=evidence))


def notify_owner(*, order: dict[str, Any], evidence: dict[str, Any] | None = None) -> str:
    """Уведомить владельца о новой оплате. "" — успех, иначе причина."""
    amount = order.get("amount_fiat", "")
    currency = order.get("currency", "USD")
    tx = order.get("txid_in") or "—"
    order_id = order.get("order_id", "")
    body = "\n".join([
        f"Paid order: {order_id}",
        f"Product: {order.get('product_id')}",
        f"Amount: {amount} {currency}",
        f"Transaction: {tx}",
        f"Status: {order.get('status')}",
        "",
        "Fulfillment is manual: send the intake form and start the audit.",
    ])
    return _send(OWNER_EMAIL, f"Nidhipati payment: {order_id} — {amount} {currency}", body)
