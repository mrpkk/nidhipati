"""Изоляция тестов от боевых файлов.

21.11.2026: `/pay/funnel` показывал товары `p` и `not-a-product` с 18 «заказами» —
это писали тесты. Владелец читает эту сводку как факт, поэтому тест не должен
видеть боевой `~/.config/nidhipati/funnel.json`.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def funnel_in_tmp(tmp_path, monkeypatch):
    from nidhipati_proof.payment_hub import checkout

    monkeypatch.setattr(checkout, "FUNNEL_PATH", tmp_path / "funnel.json")
    yield
