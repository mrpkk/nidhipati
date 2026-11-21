"""Касса считает просмотры страницы оплаты и созданные заказы.

21.11.2026: считались только заказы — «0 покупок» было неотличимо от «до кассы
не дошли». Здесь два счётчика и их отношение.
"""
from __future__ import annotations

import json

import pytest


@pytest.fixture()
def funnel(tmp_path, monkeypatch):
    from nidhipati_proof.payment_hub import checkout, web

    path = tmp_path / "funnel.json"
    monkeypatch.setattr(checkout, "FUNNEL_PATH", path)
    return path


def test_view_and_order_are_counted_separately(funnel):
    from nidhipati_proof.payment_hub import checkout

    checkout.funnel_bump("view", "karta-report")
    checkout.funnel_bump("view", "karta-report")
    checkout.funnel_bump("order", "karta-report")
    data = json.loads(funnel.read_text())
    assert data["view:karta-report"] == 2
    assert data["order:karta-report"] == 1


def test_funnel_endpoint_reports_rate(funnel):
    from nidhipati_proof.payment_hub import checkout, web

    checkout.funnel_bump("view", "karta-report")
    checkout.funnel_bump("view", "karta-report")
    checkout.funnel_bump("order", "karta-report")
    code, payload, _headers = web.handle_pay_get("/pay/funnel", {})
    assert code == 200
    row = payload["products"]["karta-report"]
    assert row["views"] == 2 and row["orders"] == 1
    assert row["view_to_order"] == "0.500"


def test_funnel_survives_missing_file(funnel):
    from nidhipati_proof.payment_hub import web

    code, payload, _ = web.handle_pay_get("/pay/funnel", {})
    assert code == 200 and payload["total_views"] == 0
