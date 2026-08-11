#!/usr/bin/env python3
"""check_conventions — Literature entry Notes.md + SanityChecks shape.

Every Literature entry must ship:
  * SanityChecks.lean
  * Notes.md sections: Informal statement, Source, Provenance, Fidelity review,
    and a pointer to SanityChecks

Also forbids re-enabling autoImplicit / native_decide / sorry inside SanityChecks.

Usage:  python ci/check_conventions.py [ROOT=formal]
Exit:   0 pass, 1 violation, 2 usage error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_NOTES = (
    "## Informal statement",
    "## Source",
    "## Provenance",
    "## Fidelity review",
)
SANITY_POINTER = re.compile(r"SanityChecks\.lean")
FORBIDDEN_SANITY = [
    (re.compile(r"\b(sorry|admit)\b"), "contains sorry/admit"),
    (re.compile(r"\bnative_decide\b"), "uses native_decide"),
    (
        re.compile(r"set_option\s+(relaxedAutoImplicit|autoImplicit)\s+true"),
        "re-enables autoImplicit",
    ),
]


def literature_entries(root: Path) -> list[Path]:
    lit = root / "Konigsberg" / "Literature"
    if not lit.is_dir():
        return []
    return sorted(
        p.parent
        for p in lit.rglob("status.toml")
    )


def check_entry(entry: Path) -> list[str]:
    errors: list[str] = []
    notes = entry / "Notes.md"
    sanity = entry / "SanityChecks.lean"

    if not sanity.exists():
        errors.append("missing SanityChecks.lean")
    else:
        text = sanity.read_text()
        if "example " not in text and "example\n" not in text:
            errors.append("SanityChecks.lean has no `example`")
        # Strip block comments so module docs mentioning `sorry` don't false-positive.
        stripped = re.sub(r"/-.*?-/", "", text, flags=re.DOTALL)
        for cre, msg in FORBIDDEN_SANITY:
            for i, line in enumerate(stripped.splitlines(), 1):
                code = line.split("--", 1)[0]
                if cre.search(code):
                    errors.append(f"SanityChecks.lean:{i}: {msg}")

    if not notes.exists():
        errors.append("missing Notes.md")
        return errors

    body = notes.read_text()
    for heading in REQUIRED_NOTES:
        if heading not in body:
            errors.append(f"Notes.md missing `{heading}`")
    if not SANITY_POINTER.search(body):
        errors.append("Notes.md missing pointer to SanityChecks.lean")
    return errors


def main(root: str = "formal") -> int:
    root_path = Path(root)
    if not root_path.exists():
        print(f"::error::root path does not exist: {root_path}")
        return 2

    total = 0
    entries = literature_entries(root_path)
    for entry in entries:
        for err in check_entry(entry):
            print(f"::error file={entry}::{err}")
            total += 1

    if total:
        print(f"check_conventions: FAIL ({total} error(s) across {len(entries)} entr(y/ies))")
        return 1
    print(f"check_conventions: OK ({len(entries)} entr(y/ies))")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
