"""Reconciliation: what is left over must be named in both directions."""

from __future__ import annotations

import csv
import json

import pytest

from nidhipati_proof.reconcile import Invoice, Tx, load_invoices, reconcile
from nidhipati_proof.reconcile_cli import main as reconcile_main


def inv(i: str = "INV-1", amount: str = "100", created: str = "2026-10-01T00:00:00Z",
        due: str | None = "2026-10-10T00:00:00Z", asset: str = "USDC", memo: str = "") -> Invoice:
    from datetime import datetime
    parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    return Invoice(id=i, amount=__import__("decimal").Decimal(amount), asset=asset,
                   created_at=parse(created), due_at=parse(due) if due else None, memo=memo)


def tx(h: str = "0x1", amount: str = "100", ts: str = "2026-10-05T00:00:00Z",
       asset: str = "USDC", memo: str = "") -> Tx:
    from datetime import datetime
    from decimal import Decimal
    return Tx(tx_hash=h, amount=Decimal(amount), asset=asset,
              ts=datetime.fromisoformat(ts.replace("Z", "+00:00")), memo=memo)


def codes(report) -> list[str]:
    return [f["code"] for f in report.findings]


def test_exact_amount_match():
    report = reconcile([inv()], [tx()])
    assert len(report.matches) == 1
    assert report.matches[0].basis == "amount"
    assert report.errors() == []


def test_memo_match_is_preferred_over_an_earlier_equal_amount():
    a, b = tx("0xearly", memo="something else"), tx("0xmemo", ts="2026-10-06T00:00:00Z", memo="INV-1")
    report = reconcile([inv()], [a, b])
    assert report.matches[0].tx.tx_hash == "0xmemo"
    assert report.matches[0].basis == "memo"


def test_unpaid_invoice_is_an_error():
    report = reconcile([inv()], [])
    assert "unpaid_invoice" in codes(report)
    assert report.unpaid_total == __import__("decimal").Decimal("100")


def test_receipt_without_invoice_is_a_warning():
    report = reconcile([], [tx()])
    assert "unmatched_receipt" in codes(report)
    assert report.errors() == []


def test_double_payment_is_reported_once_not_twice():
    report = reconcile([inv()], [tx("0x1"), tx("0x2", ts="2026-10-05T00:01:00Z")])
    assert codes(report).count("duplicate_payment") == 1
    # второй перевод не должен одновременно попасть в «без счёта»
    assert "unmatched_receipt" not in codes(report)
    assert report.unmatched_receipts == []


def test_memo_match_with_wrong_amount_is_a_mismatch():
    report = reconcile([inv()], [tx(amount="40", memo="INV-1")])
    assert "amount_mismatch" in codes(report)
    assert report.errors()


def test_late_payment_is_a_warning():
    # внутри окна оплаты (due + 1 день), но позже срока
    report = reconcile([inv()], [tx(ts="2026-10-10T12:00:00Z")])
    assert "late_payment" in codes(report)
    assert report.errors() == []


def test_same_hash_twice_is_a_broken_export():
    report = reconcile([inv("INV-1"), inv("INV-2")], [tx("0xdup"), tx("0xdup")])
    assert "duplicate_receipt" in codes(report)


def test_other_asset_does_not_match():
    report = reconcile([inv()], [tx(asset="USDT")])
    assert "unpaid_invoice" in codes(report)


def test_csv_export_lists_matched_pairs(tmp_path):
    report = reconcile([inv()], [tx()])
    out = tmp_path / "m.csv"
    report.write_csv(out)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert rows[0]["invoice_id"] == "INV-1" and rows[0]["tx_hash"] == "0x1"


def test_loader_requires_columns(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("id,amount\nINV-1,10\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        load_invoices(p)


def test_cli_exit_codes(tmp_path):
    good_i = tmp_path / "i.csv"
    good_i.write_text("id,amount,asset,created_at,due_at\n"
                      "INV-1,100,USDC,2026-10-01T00:00:00Z,2026-10-10T00:00:00Z\n", encoding="utf-8")
    good_t = tmp_path / "t.csv"
    good_t.write_text("tx_hash,amount,asset,timestamp\n"
                      "0x1,100,USDC,2026-10-05T00:00:00Z\n", encoding="utf-8")
    assert reconcile_main(["run", str(good_i), str(good_t)]) == 0

    unpaid_i = tmp_path / "i2.csv"
    # сумма не совпадает и memo нет: перевод не может закрыть этот счёт
    unpaid_i.write_text("id,amount,asset,created_at\n"
                        "INV-2,999,USDC,2026-10-01T00:00:00Z\n", encoding="utf-8")
    assert reconcile_main(["run", str(unpaid_i), str(good_t)]) == 1

    assert reconcile_main(["run", str(tmp_path / "nope.csv"), str(good_t)]) == 2
