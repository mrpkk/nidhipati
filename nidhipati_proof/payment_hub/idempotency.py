from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class InMemoryIdempotencyStore:
    """Process-local store for tests/dev. Replace with DB in production."""

    _seen: set[str] = field(default_factory=set)
    _lock: Lock = field(default_factory=Lock)

    def seen(self, key: str) -> bool:
        with self._lock:
            return key in self._seen

    def mark(self, key: str) -> bool:
        with self._lock:
            if key in self._seen:
                return False
            self._seen.add(key)
            return True
