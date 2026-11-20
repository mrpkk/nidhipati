"""Автовыдача отчёта KARTA после оплаты (хук ShellDelivery).

Проверяем три вещи, которые дороже всего стоят при ошибке:
1) без email покупателя выдача не притворяется успешной;
2) успешный скрипт (файлы + письмо) даёт ok=True;
3) падение скрипта уводит заказ в ручной разбор, а не в «выдано».
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nidhipati_proof.payment_hub.fulfillment import (  # noqa: E402
    ManualFulfillment, ShellDelivery, hook_for,
)
from nidhipati_proof.payment_hub.store import OrderRecord  # noqa: E402

import json  # noqa: E402


def _order(meta):
    return OrderRecord(order_id="o-karta", product_id="karta-report", amount_fiat="19",
                       currency="USD", status="paid", meta=meta)


def _script(tmp_path, payload: dict) -> list[str]:
    """Скрипт-заглушка: печатает JSON и принимает те же флаги, что настоящий."""
    script = tmp_path / "fake_karta.py"
    script.write_text(
        "import json,sys\n"
        f"print(json.dumps({payload!r}))\n")
    return [sys.executable, str(script)]


def test_requires_customer_email(tmp_path):
    hook = ShellDelivery(command=_script(tmp_path, {"files": {"pdf": "x"}, "emailed": True}))
    res = hook.fulfill(order=_order({}))
    assert res["ok"] is False and res["reason"] == "customer_email_missing"


def test_success_when_files_and_email(tmp_path, monkeypatch):
    monkeypatch.setenv("KARTA_REPORTS_DIR", str(tmp_path))
    hook = ShellDelivery(command=_script(tmp_path, {"files": {"pdf": "x"}, "emailed": True,
                                                    "email_reason": ""}))
    res = hook.fulfill(order=_order({"customer_email": "buyer@rta.lat"}))
    assert res["ok"] is True and res["mode"] == "shell"
    assert res["files"] == {"pdf": "x"}
    assert (tmp_path / "o-karta").exists() is False  # за нас каталог создаёт настоящий скрипт


def test_files_without_email_is_not_success(tmp_path, monkeypatch):
    monkeypatch.setenv("KARTA_REPORTS_DIR", str(tmp_path))
    hook = ShellDelivery(command=_script(tmp_path, {"files": {"pdf": "x"}, "emailed": False,
                                                    "email_reason": "smtp_credentials_missing"}))
    res = hook.fulfill(order=_order({"customer_email": "buyer@rta.lat"}))
    assert res["ok"] is False and res["emailed"] is False
    assert res["reason"] == "smtp_credentials_missing"


def test_test_address_is_blocked(tmp_path, monkeypatch):
    monkeypatch.setenv("KARTA_REPORTS_DIR", str(tmp_path))
    hook = ShellDelivery(command=_script(tmp_path, {"files": {"pdf": "x"}, "emailed": True}))
    res = hook.fulfill(order=_order({"customer_email": "buyer@example.com"}))
    assert res["ok"] is False and res["reason"] == "test_email_blocked"


def test_broken_script_goes_to_manual_review(tmp_path):
    hook = ShellDelivery(command=[sys.executable, "-c", "raise SystemExit(3)"])
    res = hook.fulfill(order=_order({"customer_email": "buyer@rta.lat"}))
    assert res["ok"] is False and res["reason"].startswith("delivery_failed")


def test_aibiz_hook_is_separate_from_karta(monkeypatch):
    """Разбор AIBiz включается своей переменной и не тянет за собой отчёт KARTA."""
    monkeypatch.delenv("KARTA_REPORT_CMD", raising=False)
    monkeypatch.setenv("AIBIZ_REVIEW_CMD", "/bin/echo aibiz")
    aibiz = hook_for(OrderRecord(order_id="o3", product_id="aibiz-review", amount_fiat="49",
                                 currency="USD", status="paid"))
    assert isinstance(aibiz, ShellDelivery)
    karta = hook_for(OrderRecord(order_id="o4", product_id="karta-report", amount_fiat="19",
                                 currency="USD", status="paid"))
    assert isinstance(karta, ManualFulfillment)


def test_hook_selected_by_product_and_env(monkeypatch):
    monkeypatch.setenv("KARTA_REPORT_CMD", "/bin/echo build")
    karta = hook_for(_order({"customer_email": "b@example.com"}))
    assert isinstance(karta, ShellDelivery)
    other = hook_for(OrderRecord(order_id="o2", product_id="root-check", amount_fiat="199",
                                 currency="USD", status="paid"))
    assert isinstance(other, ManualFulfillment)
    assert isinstance(hook_for(None), ManualFulfillment)
