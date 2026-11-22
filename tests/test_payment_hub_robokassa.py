"""Robokassa: подписи, ссылка на оплату, ответ провайдеру.

Проверяем чистую логику без сети: если подпись считается неверно, платёж не засчитается
и деньги «зависнут» — это самый дорогой вид ошибки в кассе.
"""
from __future__ import annotations

from decimal import Decimal

from nidhipati_proof.payment_hub import robokassa as rk


def test_money_format():
    assert rk.money("19") == "19.00"
    assert rk.money(Decimal("199.005")) == "199.01"
    assert rk.money(199.994) == "199.99"


def test_payment_signature_is_md5_of_protocol_string():
    sig = rk.payment_signature("shop", "1500", 42, "p1")
    # MD5("shop:1500.00:42:p1") — считаем независимо от модуля
    import hashlib
    assert sig == hashlib.md5(b"shop:1500.00:42:p1").hexdigest()


def test_result_and_success_signatures_differ():
    a = rk.result_signature("1500", 42, "p2")
    b = rk.success_signature("1500", 42, "p1")
    assert a != b
    assert len(a) == 32


def test_verify_rejects_wrong_signature():
    assert rk.verify_result("1500", 42, rk.result_signature("1500", 42, "p2"), "p2")
    assert not rk.verify_result("1500", 42, "deadbeef", "p2")
    assert not rk.verify_result("1501", 42, rk.result_signature("1500", 42, "p2"), "p2")


def test_build_payment_url_contains_required_params():
    url = rk.build_payment_url(login="shop", password1="p1", out_sum="19",
                               inv_id=1001, description="Agent Spend Audit", is_test=True)
    assert url.startswith(rk.PAYMENT_URL)
    for part in ("MerchantLogin=shop", "OutSum=19.00", "InvId=1001", "IsTest=1",
                 "SignatureValue="):
        assert part in url


def test_build_payment_url_passes_receipt_json():
    receipt = {"items": [{"name": "Аудит", "sum": 19.0, "quantity": 1}]}
    url = rk.build_payment_url(login="shop", password1="p1", out_sum="19", inv_id=7,
                               description="Аудит", receipt=receipt)
    assert "Receipt=" in url
    assert "%D0%90%D1%83%D0%B4%D0%B8%D1%82" in url  # «Аудит» в percent-encoding


def test_result_response_format():
    assert rk.result_response(1001) == "OK1001"
