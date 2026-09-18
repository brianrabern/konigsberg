"""Sufficient-only honesty for the BK reduction/discharging pair.

A miss of either half proves nothing. Tool output, Claim text, and staircase
NEXT lines must never emit the banned verdicts ``not reducible`` or
``avoidable`` (``UNAVOIDABLE`` is the one allowed positive).
"""

from __future__ import annotations

import re

# ``unavoidable`` / ``unavoidability`` are HIT language; a lookbehind keeps them.
_BANNED = re.compile(r"\bnot reducible\b|(?<!un)avoidable", re.IGNORECASE)


def assert_sufficient_only(text: str) -> str:
    """Return ``text`` or raise if a banned verdict leaked into a result string."""
    if _BANNED.search(text):
        raise RuntimeError(
            "sufficient-only invariant: must not emit 'not reducible' or "
            f"'avoidable' as a verdict (got {text!r})"
        )
    return text
