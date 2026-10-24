"""CLI for the agent spend audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .spend import audit, load_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nidhipati-spend",
        description="Audit what agents spent: duplicates, escalation, failed-but-billed, "
                    "missing refunds, runaway loops.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("audit", help="audit a CSV or JSON file of spend records")
    run.add_argument("file")
    run.add_argument("--policy", help="JSON with per-agent limits: "
                                      '{"agents": {"agent-1": {"limit_usd": "10"}}}')
    run.add_argument("--json", action="store_true", help="machine-readable report")
    run.add_argument("--out", help="write the report to this file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "audit":
        return 2
    try:
        records = load_records(args.file)
        policy = json.loads(Path(args.policy).read_text(encoding="utf-8")) if args.policy else None
        report = audit(records, policy)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    text = (json.dumps(report.as_dict(), indent=2, ensure_ascii=False)
            if args.json else report.to_markdown())
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    # 1 when money left without a reason, so CI can act on it.
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
