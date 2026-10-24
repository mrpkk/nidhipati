"""Ed25519 signing helpers (dev tooling; the client keeps the private key)."""

from __future__ import annotations

import base64
import copy
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import canonical_bytes


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    padded = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def generate_keypair() -> tuple[bytes, bytes]:
    key = Ed25519PrivateKey.generate()
    private_bytes = key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_bytes, public_bytes


def signing_payload(document: dict[str, Any]) -> bytes:
    """The signature covers the document with signature.value set to empty."""
    payload = copy.deepcopy(document)
    signature = payload.get("signature")
    if not isinstance(signature, dict):
        raise ValueError("document has no signature object")
    signature["value"] = ""
    return canonical_bytes(payload)


def sign_document(document: dict[str, Any], private_key: bytes) -> dict[str, Any]:
    key = Ed25519PrivateKey.from_private_bytes(private_key)
    signed = copy.deepcopy(document)
    signature = signed.setdefault("signature", {})
    signature.setdefault("alg", "Ed25519")
    signature.setdefault("key_id", "ed25519:dev")
    signature["value"] = b64url_encode(key.sign(signing_payload(signed)))
    return signed


def verify_signature(document: dict[str, Any], public_key: bytes) -> bool:
    signature = document.get("signature") or {}
    value = signature.get("value")
    if not isinstance(value, str) or not value:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            b64url_decode(value), signing_payload(document)
        )
    except Exception:
        return False
    return True


def write_keypair(out_dir: str | Path) -> tuple[Path, Path, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    private_bytes, public_bytes = generate_keypair()
    private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
    public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
    private_path = out / "private.pem"
    public_path = out / "public.pem"
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path, b64url_encode(public_bytes)


def load_private_key(path: str | Path) -> bytes:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("not an Ed25519 private key")
    return key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )


def load_public_key(path: str | Path) -> bytes:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("not an Ed25519 public key")
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
