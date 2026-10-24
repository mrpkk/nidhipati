"""CLI for the reserve and NAV report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .reserve import build_report, load_reserve
from .sign import load_private_key, sign_document


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
        print(f"wrote {args.out}")
    else:
        print(text)
    if args.markdown:
        Path(args.markdown).write_text(report.to_markdown() + "\n", encoding="utf-8")
        print(f"wrote {args.markdown}")

    return 0 if not report.errors() else 1


if __name__ == "__main__":
    raise SystemExit(main())
