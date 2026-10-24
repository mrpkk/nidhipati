"""The browser audit and the CLI must agree on the same file.

The site says "the same checks". Before this guard they did not: the browser
omitted price_escalation from the "spent without a reason" sum and only knew a
single flat budget, so the same sample read 0.11 / budget_bypass in a browser and
0.14 / budget_exceeded in the CLI. A visitor comparing the two would catch us
lying, and they would be right.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from nidhipati_proof.spend import audit, load_records

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "examples" / "spend-sample.csv"
POLICY = ROOT / "examples" / "spend-policy.example.json"
NODE = shutil.which("node")


def python_view() -> dict:
    report = audit(load_records(SAMPLE), json.loads(POLICY.read_text(encoding="utf-8")))
    return {
        "counts": dict(Counter(f.code for f in report.findings)),
        "no_reason": report.estimated_overpay,
        "above_usual": report.overpay_vs_median,
        "over_budget": report.budget_overrun,
    }


@pytest.mark.skipif(NODE is None, reason="node не установлен")
def test_browser_and_cli_report_the_same_numbers():
    out = subprocess.run(
        [NODE, str(ROOT / "tools" / "parity_check.cjs"), str(SAMPLE), str(POLICY)],
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr
    js = json.loads(out.stdout)
    py = python_view()

    assert js["counts"] == py["counts"]
    for key in ("no_reason", "above_usual", "over_budget"):
        assert Decimal(str(js[key])).quantize(Decimal("0.01")) == py[key].quantize(Decimal("0.01")), key


@pytest.mark.skipif(NODE is None, reason="node не установлен")
def test_browser_still_flags_a_bypass_when_no_policy_is_given():
    out = subprocess.run(
        [NODE, str(ROOT / "tools" / "parity_check.cjs"), str(SAMPLE)],
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stderr
    js = json.loads(out.stdout)
    assert "budget_bypass" in js["counts"]
    assert "budget_exceeded" not in js["counts"]
