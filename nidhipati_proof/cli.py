"""CLI for Nidhipati Proof of Spend v0.1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .sign import load_private_key, load_public_key, sign_document, write_keypair
from .verify import verify_document, verify_invoice


def _read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str, data: dict) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nidhipati-proof", description="Proof of Spend v0.1")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="verify a signed Proof of Spend document")
    verify.add_argument("file")
    verify.add_argument("--pubkey", required=True, help="public key: PEM file, base64url, or hex")
    verify.add_argument("--json", action="store_true", help="print machine-readable JSON")

    keygen = sub.add_parser("keygen", help="generate Ed25519 keypair")
    keygen.add_argument("--out-dir", default="keys")

    sign = sub.add_parser("sign", help="sign a document with a private key (dev helper)")
    sign.add_argument("file")
    sign.add_argument("--key", required=True, help="private key PEM")
    sign.add_argument("--out", help="output path (default: <file>.signed.json)")
    return parser


def _join_leading_dash(argv: list[str]) -> list[str]:
    """`--pubkey -abc…`: base64url может начинаться с дефиса, и argparse читает его как флаг.

    Около 1.5 % ключей (1/64) начинаются с `-`. Склеиваем значение с флагом через `=`,
    чтобы такой ключ принимался как обычный.
    """
    out: list[str] = []
    i = 0
    while i < len(argv):
        item = argv[i]
        if item.startswith("--") and "=" not in item and i + 1 < len(argv) \
                and argv[i + 1].startswith("-") and argv[i + 1] != "-":
            out.append(f"{item}={argv[i + 1]}")
            i += 2
            continue
        out.append(item)
        i += 1
    return out


def main(argv: list[str] | None = None) -> int:
    argv = _join_leading_dash(list(sys.argv[1:] if argv is None else argv))
    args = build_parser().parse_args(argv)
    if args.command == "keygen":
        private_path, public_path, public_b64 = write_keypair(args.out_dir)
        print(f"private: {private_path}")
        print(f"public:  {public_path}")
        print(f"pubkey:  {public_b64}")
        return 0

    if args.command == "sign":
        document = _read_json(args.file)
        signed = sign_document(document, load_private_key(args.key))
        out = args.out or f"{args.file}.signed.json"
        _write_json(out, signed)
        print(f"wrote {out}")
        return 0

    if args.command == "verify":
        try:
            document = _read_json(args.file)
        except Exception as exc:
            print(f"error: cannot read {args.file}: {exc}", file=sys.stderr)
            return 2
        pub = args.pubkey
        if Path(pub).exists():
            try:
                public_key = load_public_key(pub)
            except Exception as exc:
                print(f"error: cannot load public key: {exc}", file=sys.stderr)
                return 2
        else:
            public_key = pub
        result = verify_invoice(document, public_key) if "invoice" in document else verify_document(document, public_key)
        if args.json:
            print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
        else:
            print("OK" if result.ok else "FAIL")
            for check, value in result.checks.items():
                print(f"  {'✓' if value.ok else '✗'} {check}: {value.detail}")
            for error in result.errors:
                print(f"  error: {error}", file=sys.stderr)
            for warning in result.warnings:
                print(f"  warning: {warning}")
        return 0 if result.ok else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
