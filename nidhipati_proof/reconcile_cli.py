"""CLI for invoice/transfer reconciliation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .reconcile import load_invoices, load_transactions, reconcile
from .sign import load_private_key, sign_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nidhipati-reconcile",
        description="Match invoices against transfers and name what is left over in both "
                    "directions.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="reconcile two files")
    run.add_argument("invoices")
    run.add_argument("transactions")
    run.add_argument("--key", help="private key PEM: sign the report")
    run.add_argument("--out", help="write JSON here (default: stdout)")
    run.add_argument("--markdown", help="also write a Markdown report here")
    run.add_argument("--csv", help="also write matched pairs as CSV")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "run":
        return 2
    try:
        report = reconcile(load_invoices(args.invoices), load_transactions(args.transactions))
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
    if args.csv:
        report.write_csv(args.csv)
        print(f"wrote {args.csv}", file=sys.stderr)
    return 0 if not report.errors() else 1


if __name__ == "__main__":
    raise SystemExit(main())
