"""Robokassa: приём карт РФ (и иностранных по тарифу 9,9 %) без зарубежного юрлица.

Рельс нужен для продаж внутри России: ЮKassa/Robokassa принимают рубли с карт РФ,
в отличие от PayGate (карты → USDC).

Документация: https://docs.robokassa.ru/ — подпись MD5 от строки параметров.
Здесь только чистая логика без сети: сборка платёжной ссылки, проверка подписей
Result URL (сервер-сервер) и Success URL (возврат пользователя), ответ провайдеру.

Все суммы — Decimal с двумя знаками: float в деньгах недопустим.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import urllib.parse
from decimal import Decimal, ROUND_HALF_UP

PAYMENT_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


def money(amount: Decimal | str | int | float) -> str:
    """Сумма в формате провайдера: два знака, точка, без пробелов."""
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{value:.2f}"


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()  # noqa: S324 - протокол провайдера


def payment_signature(login: str, out_sum: str, inv_id: int, password1: str) -> str:
    """SignatureValue для платёжной ссылки: MD5(login:OutSum:InvId:Password1)."""
    return _md5(f"{login}:{money(out_sum)}:{inv_id}:{password1}")


def result_signature(out_sum: str, inv_id: int, password2: str) -> str:
    """SignatureValue для Result URL: MD5(OutSum:InvId:Password2)."""
    return _md5(f"{money(out_sum)}:{inv_id}:{password2}")


def success_signature(out_sum: str, inv_id: int, password1: str) -> str:
    """SignatureValue для Success URL: MD5(OutSum:InvId:Password1)."""
    return _md5(f"{money(out_sum)}:{inv_id}:{password1}")


def build_payment_url(
    *,
    login: str,
    password1: str,
    out_sum: Decimal | str,
    inv_id: int,
    description: str,
    is_test: bool = False,
    receipt: dict | None = None,
    email: str | None = None,
) -> str:
    """Ссылка на оплату. receipt — чек для 54-ФЗ (передаётся JSON-строкой)."""
    params = {
        "MerchantLogin": login,
        "OutSum": money(out_sum),
        "InvId": str(inv_id),
        "Description": description[:100],
        "SignatureValue": payment_signature(login, out_sum, inv_id, password1),
    }
    if email:
        params["Email"] = email
    if receipt is not None:
        params["Receipt"] = json.dumps(receipt, ensure_ascii=False, separators=(",", ":"))
    if is_test:
        params["IsTest"] = "1"
    return f"{PAYMENT_URL}?{urllib.parse.urlencode(params)}"


def verify_signature(expected: str, provided: str) -> bool:
    """Сравнение подписей без утечки по времени."""
    return hmac.compare_digest(expected.lower(), (provided or "").lower())


def verify_result(out_sum: str, inv_id: int, signature: str, password2: str) -> bool:
    return verify_signature(result_signature(out_sum, inv_id, password2), signature)


def verify_success(out_sum: str, inv_id: int, signature: str, password1: str) -> bool:
    return verify_signature(success_signature(out_sum, inv_id, password1), signature)


def result_response(inv_id: int) -> str:
    """Ответ на Result URL, который Robokassa ждёт для подтверждения оплаты."""
    return f"OK{inv_id}"
