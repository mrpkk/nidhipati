"""Reserve report: a ratio is refused when a line has no price, and a fake number never appears."""

from __future__ import annotations

import json
from decimal import Decimal as D

import pytest

from nidhipati_proof.reserve import build_report
from nidhipati_proof.reserve_cli import main as reserve_main
from nidhipati_proof.sign import generate_keypair, sign_document, verify_signature


def base(**over) -> dict:
    doc = {
        "issuer": "Test Issuer",
        "token": "TUSD",
        "as_of": "2026-10-25T00:00:00Z",
        "supply": {"value": "1000"},
        "reserve": [
            {"asset": "USDC", "kind": "stablecoin", "quantity": "600", "price": "1.00",
             "price_as_of": "2026-10-24T00:00:00Z", "source": "statement line 1"},
            {"asset": "T-BILL", "kind": "treasury", "quantity": "400", "price": "1.00",
             "price_as_of": "2026-10-24T00:00:00Z", "source": "statement line 2"},
        ],
    }
    doc.update(over)
    return doc


def codes(report) -> list[str]:
    return [f["code"] for f in report.findings]


def test_backed_reserve_with_liabilities():
    doc = base()
    doc["reserve"][0]["quantity"] = "620"
    doc["reserve"][1]["quantity"] = "400"
    doc["liabilities"] = [{"asset": "fee", "quantity": "20", "price": "1.00", "source": "fee schedule"}]
    report = build_report(doc)
    assert report.nav == D("1000.00")
    assert report.backing_ratio == D("1.0000")
    assert report.verdict == "backed"
    assert report.errors() == []


def test_unpriced_line_refuses_the_ratio():
    doc = base()
    del doc["reserve"][1]["price"]
    report = build_report(doc)
    assert report.verdict == "incomplete"
    assert report.backing_ratio is None
    assert report.nav_complete is False
    assert "unpriced" in codes(report)


def test_missing_source_is_an_error_not_a_blank():
    doc = base()
    doc["reserve"][0]["source"] = ""
    report = build_report(doc)
    assert "missing_source" in codes(report)
    assert report.errors()


def test_underbacked_reserve_is_named():
    doc = base()
    doc["reserve"][0]["quantity"] = "500"
    doc["reserve"][1]["quantity"] = "300"
    report = build_report(doc)
    assert report.verdict == "underbacked"
    assert report.backing_ratio == D("0.8000")
    assert "underbacked" in codes(report)


def test_stale_price_is_a_warning():
    doc = base()
    doc["reserve"][0]["price_as_of"] = "2026-10-01T00:00:00Z"
    report = build_report(doc)
    assert "stale_price" in codes(report)
    assert report.errors() == []


def test_haircut_out_of_range_is_an_error():
    doc = base()
    doc["reserve"][0]["haircut"] = "1.5"
    report = build_report(doc)
    assert "haircut_out_of_range" in codes(report)


def test_statement_hash_mismatch_is_caught(tmp_path):
    statement = tmp_path / "statement.txt"
    statement.write_text("balance: 1000\n", encoding="utf-8")
    doc = base(statement={"hash": "sha256:" + "0" * 64, "path": "statement.txt"})
    report = build_report(doc, base_dir=tmp_path)
    assert "statement_hash_mismatch" in codes(report)


def test_statement_hash_matches_the_file(tmp_path):
    statement = tmp_path / "s.txt"
    statement.write_text("balance: 1000\n", encoding="utf-8")
    import hashlib
    digest = hashlib.sha256(statement.read_bytes()).hexdigest()
    doc = base(statement={"hash": f"sha256:{digest}", "path": "s.txt"})
    report = build_report(doc, base_dir=tmp_path)
    assert "statement_hash_mismatch" not in codes(report)
    assert report.statement_computed == digest


def test_missing_supply_blocks_the_verdict():
    doc = base()
    del doc["supply"]
    report = build_report(doc)
    assert "missing_supply" in codes(report)
    assert report.backing_ratio is None


def test_as_of_is_required():
    doc = base()
    del doc["as_of"]
    with pytest.raises(ValueError, match="as_of"):
        build_report(doc)


def test_report_can_be_signed_and_verified(tmp_path):
    private_key, public_key = generate_keypair()
    document = sign_document(build_report(base()).as_dict(), private_key)
    assert verify_signature(document, public_key)
    document["nav"] = "999999"
    assert not verify_signature(document, public_key)


def test_markdown_states_the_disclaimer_and_the_ratio():
    text = build_report(base()).to_markdown()
    assert "Not a statutory audit" in text
    assert "Backing ratio" in text
    assert "sha256:" in text


def test_cli_exit_codes(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(base()), encoding="utf-8")
    assert reserve_main(["report", str(good)]) == 0

    broken = tmp_path / "broken.json"
    doc = base()
    del doc["reserve"][0]["price"]
    broken.write_text(json.dumps(doc), encoding="utf-8")
    assert reserve_main(["report", str(broken)]) == 1

    assert reserve_main(["report", str(tmp_path / "nope.json")]) == 2


def test_cli_writes_markdown(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(base()), encoding="utf-8")
    md = tmp_path / "report.md"
    assert reserve_main(["report", str(good), "--markdown", str(md)]) == 0
    assert "Reserve and NAV report" in md.read_text(encoding="utf-8")
