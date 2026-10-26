"""CLI for the reserve and NAV report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .reserve import build_report, load_reserve
from .sign import (b64url_decode, load_private_key, load_public_key, sign_document,
                   verify_signature)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nidhipati-reserve",
        description="Build a reserve and NAV report: explicit formulas, evidence per line, "
                    "and no ratio when a line has no price.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("report", help="build a report from a JSON description")
    run.add_argument("file")
    run.add_argument("--key", help="private key PEM: sign the report")
    run.add_argument("--out", help="write JSON here (default: stdout)")
    run.add_argument("--markdown", help="also write a Markdown report here")

    check = sub.add_parser("verify", help="verify the Ed25519 signature on a report")
    check.add_argument("file")
    check.add_argument("--pubkey", required=True,
                       help="public key: PEM file, base64url, or hex")
    check.add_argument("--json", action="store_true", help="machine-readable result")
    return parser


def _public_key_bytes(text: str) -> bytes:
    """A PEM path, a base64url key, or a hex key — whichever the buyer was given."""
    path = Path(text)
    if path.is_file():
        return load_public_key(path)
    value = text.strip()
    if value.startswith("0x") or all(c in "0123456789abcdefABCDEF" for c in value):
        raw = bytes.fromhex(value[2:] if value.startswith("0x") else value)
    else:
        raw = b64url_decode(value)
    if len(raw) != 32:
        raise ValueError("Ed25519 public key must be 32 bytes")
    return raw


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "verify":
        try:
            document = json.loads(Path(args.file).read_text(encoding="utf-8"))
            public_key = _public_key_bytes(args.pubkey)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        valid = verify_signature(document, public_key)
        verdict = str(document.get("verdict") or "unknown")
        result = {"signature": valid, "verdict": verdict,
                  "issuer": document.get("issuer"),
                  "token": document.get("token"),
                  "as_of": document.get("as_of")}
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"signature: {'valid' if valid else 'invalid'}")
            print(f"verdict: {verdict}")
        return 0 if valid else 1
    if args.command != "report":
        return 2
    try:
        data = load_reserve(args.file)
        report = build_report(data, base_dir=Path(args.file).parent)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    document = report.as_dict()
    if args.key:
        document = sign_document(document, load_private_key(args.key))

    text = json.dumps(document, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    if args.markdown:
        Path(args.markdown).write_text(report.to_markdown() + "\n", encoding="utf-8")
        print(f"wrote {args.markdown}", file=sys.stderr)

    return 0 if not report.errors() else 1


if __name__ == "__main__":
    raise SystemExit(main())
