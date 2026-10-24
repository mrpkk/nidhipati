"""Deterministic JSON encoding used for signing and verification.

This is sorted-key, compact UTF-8 JSON. It is deliberately simple and stated
as the v0.1 canonical form in the spec; a future version can adopt RFC 8785
and keep this as a legacy test vector.
"""

from __future__ import annotations

import json
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def canonical_text(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")
