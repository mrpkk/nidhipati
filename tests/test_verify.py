import copy
import json
from pathlib import Path

from nidhipati_proof.cli import main
from nidhipati_proof.sign import b64url_encode, generate_keypair, sign_document
from nidhipati_proof.verify import verify_document

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "proof-of-spend.example.json"


def base_doc():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def signed(doc, private_key):
    return sign_document(doc, private_key)


def test_valid_document():
    private, public = generate_keypair()
    doc = signed(base_doc(), private)
    result = verify_document(doc, public)
    assert result.ok, result.errors
    assert result.onchain_verified is False


def test_bad_signature_after_tamper():
    private, public = generate_keypair()
    doc = signed(base_doc(), private)
    doc["payment"]["amount"] = "0.06"
    result = verify_document(doc, public)
    assert not result.ok
    assert result.checks["signature"].ok is False


def test_expired_mandate():
    private, public = generate_keypair()
    doc = base_doc()
    doc["mandate"]["expires_at"] = "2026-10-24T11:00:00Z"
    doc = signed(doc, private)
    result = verify_document(doc, public)
    assert not result.ok
    assert result.checks["mandate_expiry"].ok is False


def test_usage_mismatch():
    private, public = generate_keypair()
    doc = base_doc()
    doc["usage"]["quantity"] = "2"
    doc = signed(doc, private)
    result = verify_document(doc, public)
    assert not result.ok
    assert result.checks["usage_amount"].ok is False


def test_refund_above_payment():
    private, public = generate_keypair()
    doc = base_doc()
    doc["refund"]["amount"] = "1"
    doc = signed(doc, private)
    result = verify_document(doc, public)
    assert not result.ok
    assert result.checks["refund"].ok is False


def test_denied_verdict():
    private, public = generate_keypair()
    doc = base_doc()
    doc["verdict"]["decision"] = "deny"
    doc = signed(doc, private)
    result = verify_document(doc, public)
    assert not result.ok
    assert result.checks["verdict_allow"].ok is False


def test_missing_receipt_id():
    private, public = generate_keypair()
    doc = base_doc()
    doc["receipt_id"] = ""
    doc = signed(doc, private)
    result = verify_document(doc, public)
    assert not result.ok
    assert result.checks["schema"].ok is False


def test_wrong_algorithm():
    private, public = generate_keypair()
    doc = base_doc()
    doc["signature"]["alg"] = "HMAC"
    doc = signed(doc, private)
    result = verify_document(doc, public)
    assert not result.ok
    assert result.checks["signature_alg"].ok is False


def test_bad_public_key():
    private, _ = generate_keypair()
    doc = signed(base_doc(), private)
    result = verify_document(doc, "not-a-key")
    assert not result.ok
    assert result.checks["signature"].ok is False


def test_cli_verify_valid_and_invalid(tmp_path):
    private, public = generate_keypair()
    doc = signed(base_doc(), private)
    good = tmp_path / "good.json"
    good.write_text(json.dumps(doc), encoding="utf-8")
    pubkey = b64url_encode(public)
    assert main(["verify", str(good), "--pubkey", pubkey, "--json"]) == 0

    bad = copy.deepcopy(doc)
    bad["payment"]["amount"] = "9"
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(bad), encoding="utf-8")
    assert main(["verify", str(bad_path), "--pubkey", pubkey, "--json"]) == 1
