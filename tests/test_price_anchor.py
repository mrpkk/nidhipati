"""Якорь founding-цены: без него $19 выглядит обычной ценой, а не скидкой с $199."""
from __future__ import annotations

import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pc", BASE / "scripts" / "price_consistency.py")
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)

KNOWN = {"agent-spend-audit": 199, "agent-spend-audit-founding": 19, "sheet-doctor": 19}


def test_missing_anchor_is_warned():
    text = 'href="/pay/card?product=agent-spend-audit-founding" $19 founding'
    issues = pc.scan_text(text, KNOWN)
    assert any(i["level"] == "warn" and "якор" in i["why"] for i in issues)


def test_present_anchor_passes():
    text = 'href="/pay/card?product=agent-spend-audit-founding" was $199 now $19'
    assert not [i for i in pc.scan_text(text, KNOWN) if "якор" in i["why"]]


def test_real_pages_have_no_anchor_warnings():
    res = pc.run()
    assert res["errors"] == 0
    assert not [i for i in res["issues"] if "якор" in i["why"]], res["issues"]
