"""Optional Sage backend for standard graph queries (open decision #2)."""
from __future__ import annotations


def available() -> bool:
    try:
        import sage  # noqa: F401
        return True
    except ImportError:
        return False
