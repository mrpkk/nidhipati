"""Spend audit: every finding must name the row, and a clean file must stay clean."""

from __future__ import annotations

import json
from decimal import Decimal as D
from pathlib import Path

import pytest

from nidhipati_proof.spend import audit, load_records
from nidhipati_proof.spend_cli import main as spend_main

BASE = {"tool": "llm.complete", "model": "gpt-4o-mini", "quote": "0.02", "settled": "0.02",
        "actual": "0.02", "refund": "0", "asset": "USDC", "network": "base",
        "payee": "0xpay", "status": "ok"}


def row(ts: str = "2026-10-01T10:00:00Z", agent: str = "agent-1", **over) -> dict:
    r = {"ts": ts, "agent_id": agent, **BASE}
    r.update({k: str(v) for k, v in over.items()})
    return r


def codes(report) -> list[str]:
    return [f.code for f in report.findings]


def test_clean_records_produce_no_finding():
    report = audit([row("2026-10-01T10:00:00Z"), row("2026-10-01T10:05:00Z", tool="search")])
    # Nothing wrong with the money. The only note is that no policy file was given:
    # without it a budget lives in a prompt, and a prompt is not a limit.
    assert [f.code for f in report.findings] == ["budget_bypass"]
    assert report.total_settled == D("0.04")
    assert report.errors == []


def test_duplicate_tx_is_an_error_with_evidence():
    a = row(tx_hash="0xdead")
    b = row("2026-10-01T11:00:00Z", tx_hash="0xdead")
    report = audit([a, b])
    dup = [f for f in report.findings if f.code == "duplicate_charge"]
    assert dup and dup[0].severity == "error"
    assert "0xdead" in dup[0].evidence


def test_two_receipts_are_two_payments_not_a_duplicate():
    """Баг 25.10: одинаковые суммы в цикле считались дублями и раздували отчёт."""
    rows = [row(f"2026-10-01T10:00:{i:02d}Z", agent="agent-loop",
                quote="0.001", settled="0.001", actual="0.001",
                tx_hash=f"0x{i:04d}") for i in range(20)]
    report = audit(rows)
    assert "duplicate_charge" not in codes(report)
    assert report.estimated_overpay == D("0")


def test_equal_charge_within_window_is_a_duplicate():
    report = audit([row("2026-10-01T10:00:00Z"), row("2026-10-01T10:00:40Z")])
    assert "duplicate_charge" in codes(report)


def test_price_escalation_reports_the_excess():
    report = audit([row(settled="0.05", actual="0.05")])
    finding = next(f for f in report.findings if f.code == "price_escalation")
    assert finding.amount == D("0.03")
    assert report.estimated_overpay == D("0.03")


def test_failed_call_that_cost_money_is_an_error():
    report = audit([row(status="failed")])
    assert "failed_but_billed" in codes(report)
    assert report.errors


def test_missing_refund_is_named_with_the_unreturned_amount():
    report = audit([row(quote="0.10", settled="0.10", actual="0.04")])
    finding = next(f for f in report.findings if f.code == "missing_refund")
    assert finding.amount == D("0.06")


def test_runaway_loop_is_caught_per_agent():
    rows = [row(f"2026-10-01T10:00:{i:02d}Z", agent="agent-loop") for i in range(31)]
    report = audit(rows)
    assert "runaway_loop" in codes(report)


def test_unknown_asset_network_and_missing_payee_are_warnings():
    report = audit([row(asset="MOON", network="moonnet", payee="")])
    assert {"unknown_asset", "unknown_network", "missing_payee"} <= set(codes(report))
    assert report.errors == []


def test_model_overpay_is_an_estimate_above_the_median():
    rows = [row("2026-10-01T10:00:00Z"), row("2026-10-01T10:10:00Z"),
            row("2026-10-01T10:20:00Z"), row("2026-10-01T10:30:00Z",
                                            settled="0.30", actual="0.30", quote="0.30")]
    report = audit(rows)
    finding = next(f for f in report.findings if f.code == "model_overpay")
    assert finding.severity == "warning"
    assert finding.amount == D("0.28")
    # оценка «дороже обычного» не смешивается с деньгами без основания
    assert report.estimated_overpay == D("0")
    assert report.overpay_vs_median == D("0.28")


def test_policy_turns_a_prompt_limit_into_a_real_one():
    rows = [row("2026-10-01T10:00:00Z"), row("2026-10-01T10:05:00Z")]
    no_policy = audit(rows)
    assert "budget_bypass" in codes(no_policy)

    with_policy = audit(rows, {"agents": {"agent-1": {"limit_usd": "0.01"}}})
    exceeded = next(f for f in with_policy.findings if f.code == "budget_exceeded")
    assert exceeded.severity == "error"
    assert exceeded.amount == D("0.03")
    assert with_policy.budget_overrun == D("0.03")
    assert with_policy.estimated_overpay == D("0")


def test_loader_refuses_a_file_without_the_required_column(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("ts,agent_id,tool,quote\n2026-10-01T10:00:00Z,a,t,0.02\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        load_records(p)


def test_loader_reads_json_records(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({"records": [row()]}), encoding="utf-8")
    assert len(load_records(p)) == 1


def test_cli_exit_codes_follow_the_money(tmp_path, capsys):
    clean = tmp_path / "clean.csv"
    clean.write_text("ts,agent_id,tool,quote,settled,status\n"
                     "2026-10-01T10:00:00Z,a,llm.complete,0.02,0.02,ok\n", encoding="utf-8")
    assert spend_main(["audit", str(clean), "--json"]) == 0

    dirty = tmp_path / "dirty.csv"
    dirty.write_text("ts,agent_id,tool,quote,settled,status\n"
                     "2026-10-01T10:00:00Z,a,llm.complete,0.02,0.05,failed\n", encoding="utf-8")
    assert spend_main(["audit", str(dirty), "--json"]) == 1

    missing = tmp_path / "nope.csv"
    assert spend_main(["audit", str(missing)]) == 2


def test_markdown_says_it_is_an_estimate():
    report = audit([row(settled="0.05", actual="0.05")])
    text = report.to_markdown()
    assert "spent without a reason" in text
    assert "Estimates from the records provided" in text
    assert "nothing was verified on-chain" in text.lower()
