"""A USDC invoice is not a receipt; its signature is checked by the same CLI."""

import json

from nidhipati_proof.cli import main as proof_main
from nidhipati_proof.sign import b64url_encode, generate_keypair, sign_document


def invoice_doc():
    return {
        "invoice": {
            "id": "NID-2026-0001",
            "issued_at": "2026-10-27T00:00:00Z",
            "due_at": "2026-11-03T00:00:00Z",
            "seller": "Nidhipati",
            "buyer": "Example Client",
            "service": "Reserve disclosure review",
            "amount": {"value": "250.00", "asset": "USDC", "network": "eip155:8453"},
            "pay_to": "0x0000000000000000000000000000000000000001",
            "terms": "Payment before delivery.",
        }
    }


def test_signed_invoice_verifies(tmp_path, capsys):
    private, public = generate_keypair()
    doc = sign_document(invoice_doc(), private)
    path = tmp_path / "invoice.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert proof_main(["verify", str(path), "--pubkey", b64url_encode(public)]) == 0
    out = capsys.readouterr().out
    assert "OK" in out
    assert "pay_to" in out


def test_tampered_invoice_fails(tmp_path):
    private, public = generate_keypair()
    doc = sign_document(invoice_doc(), private)
    doc["invoice"]["amount"]["value"] = "1.00"
    path = tmp_path / "invoice.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert proof_main(["verify", str(path), "--pubkey", b64url_encode(public)]) == 1
