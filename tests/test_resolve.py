"""Resolution evidence: a conflict must be called a conflict, not averaged away."""

from __future__ import annotations

import json

import pytest

from nidhipati_proof.resolve import build_report
from nidhipati_proof.resolve_cli import main as resolve_main


def market(**over) -> dict:
    doc = {
        "market_id": "M-1",
        "question": "Did X ship before the deadline?",
        "deadline": "2026-11-01T00:00:00Z",
        "declared": {"outcome": "YES", "at": "2026-11-02T10:00:00Z", "by": "resolver"},
        "sources": [
            {"name": "notes", "claim": "YES", "quote": "v2 released on 29 October",
             "retrieved_at": "2026-11-02T09:00:00Z"},
            {"name": "explorer", "claim": "YES", "quote": "first v2 transaction at block 21M",
             "retrieved_at": "2026-11-02T09:10:00Z"},
        ],
    }
    doc.update(over)
    return doc


def codes(report) -> list[str]:
    return [f["code"] for f in report.findings]


def test_two_agreeing_sources_support_the_outcome():
    report = build_report(market())
    assert report.verdict == "supported"
    assert report.errors() == []


def test_a_contradicting_source_makes_it_disputed():
    doc = market()
    doc["sources"].append({"name": "third", "claim": "NO", "quote": "v2 not deployed here",
                           "retrieved_at": "2026-11-02T09:20:00Z"})
    report = build_report(doc)
    assert report.verdict == "disputed"
    assert "sources_conflict" in codes(report)


def test_all_sources_against_the_declaration():
    doc = market()
    for s in doc["sources"]:
        s["claim"] = "NO"
    report = build_report(doc)
    assert report.verdict == "disputed"
    assert "source_contradicts" in codes(report)


def test_missing_quote_is_insufficient_even_when_everyone_agrees():
    doc = market()
    del doc["sources"][0]["quote"]
    report = build_report(doc)
    assert "missing_evidence" in codes(report)
    assert report.verdict == "insufficient"


def test_one_source_is_not_a_settlement():
    doc = market()
    doc["sources"] = doc["sources"][:1]
    report = build_report(doc)
    assert report.verdict == "single_source"
    assert "single_source" in codes(report)


def test_source_before_the_deadline_cannot_settle():
    doc = market()
    doc["sources"][0]["retrieved_at"] = "2026-10-20T00:00:00Z"
    report = build_report(doc)
    assert "pre_deadline_source" in codes(report)


def test_premature_resolution_is_a_warning():
    doc = market(declared={"outcome": "YES", "at": "2026-10-31T23:00:00Z", "by": "resolver"})
    report = build_report(doc)
    assert "premature_resolution" in codes(report)


def test_unknown_outcome_blocks_a_verdict():
    doc = market(declared={"outcome": "MAYBE", "at": "2026-11-02T10:00:00Z", "by": "resolver"})
    report = build_report(doc)
    assert report.verdict == "insufficient"
    assert "unknown_outcome" in codes(report)


def test_no_sources_is_an_error():
    report = build_report(market(sources=[]))
    assert report.verdict == "insufficient"
    assert "no_sources" in codes(report)


def test_rules_hash_mismatch_is_caught(tmp_path):
    rules = tmp_path / "rules.md"
    rules.write_text("The market resolves YES if v2 ships.\n", encoding="utf-8")
    doc = market(rules_hash="sha256:" + "0" * 64, rules={"path": "rules.md"})
    report = build_report(doc, base_dir=tmp_path)
    assert "rules_hash_mismatch" in codes(report)


def test_missing_declared_at_is_refused():
    doc = market()
    del doc["declared"]["at"]
    with pytest.raises(ValueError, match="declared.at"):
        build_report(doc)


def test_cli_exit_codes(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(market()), encoding="utf-8")
    assert resolve_main(["report", str(good)]) == 0

    disputed = market()
    disputed["sources"].append({"name": "third", "claim": "NO", "quote": "denied",
                                "retrieved_at": "2026-11-02T09:30:00Z"})
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(disputed), encoding="utf-8")
    assert resolve_main(["report", str(bad)]) == 1

    assert resolve_main(["report", str(tmp_path / "nope.json")]) == 2


def test_markdown_carries_the_disclaimer():
    text = build_report(market()).to_markdown()
    assert "Not a statutory audit and not trading" in text
    assert "Verdict" in text
