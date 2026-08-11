#!/usr/bin/env python3
"""check_no_sorry — cheap static gate.

An entry whose status.toml declares any claim `formalized` must have a
`Proofs.lean` with no `sorry`/`admit`. Entries that are only `stated` may (and
usually do) contain `sorry` — that is what `stated` means.

This is a FAST PRE-FILTER, not the authoritative check. The authoritative,
per-declaration gate is check_axioms.py: a `sorry` shows up in `#print axioms`
as `sorryAx`, so anything formalized-but-actually-sorried is caught there even
if it slips past this token scan.

Convention it relies on: one entry directory == one formalization unit, with
proofs in `Proofs.lean`. Mixed entries (some claims formalized, some stated, in
the same proof file) are not distinguishable statically here — keep them
separate, or rely on check_axioms for the fine-grained verdict.

Usage:  python ci/check_no_sorry.py [ROOT=formal]
Exit:   0 clean, 1 violation, 2 usage/parse error.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

FORBIDDEN = re.compile(r"\b(sorry|admit)\b")


def entry_is_formalized(status_path: Path) -> bool:
    try:
        data = tomllib.loads(status_path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"::error file={status_path}::unreadable status.toml: {e}")
        raise
    return any(c.get("status") == "formalized" for c in data.get("claims", []))


def main(root: str = "formal") -> int:
    root_path = Path(root)
    if not root_path.exists():
        print(f"::error::root path does not exist: {root_path}")
        return 2

    violations = 0
    parse_errors = 0
    for status_path in sorted(root_path.rglob("status.toml")):
        try:
            if not entry_is_formalized(status_path):
                continue
        except tomllib.TOMLDecodeError:
            parse_errors += 1
            continue

        proofs = status_path.with_name("Proofs.lean")
        if not proofs.exists():
            print(f"::error file={status_path}::formalized entry has no Proofs.lean")
            violations += 1
            continue

        for lineno, line in enumerate(proofs.read_text().splitlines(), 1):
            code = line.split("--", 1)[0]  # ignore line comments
            if FORBIDDEN.search(code):
                print(
                    f"::error file={proofs},line={lineno}::"
                    f"'{FORBIDDEN.search(code).group(0)}' in a formalized entry"
                )
                violations += 1

    if parse_errors:
        return 2
    if violations:
        print(f"check_no_sorry: FAIL ({violations} violation(s))")
        return 1
    print("check_no_sorry: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
