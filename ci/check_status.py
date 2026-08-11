#!/usr/bin/env python3
"""check_status — schema and consistency gate for status.toml.

Enforces that every status.toml is well-formed and internally consistent, so the
other gates and the runtime ledger can trust its shape:

  * [entry] has name, citation, area.
  * every [[claims]] has lean_name, status, verified_at.
  * status is one of: formalized | stated | informal.
  * a `formalized` claim carries an `axioms` field (possibly empty list) — the
    field must exist so check_axioms has something to validate.
  * lean_name is namespaced under Konigsberg.Literature.* or Konigsberg.Areas.*.
  * `formalized` with `sorryAx` recorded is an immediate contradiction.

This does NOT run Lean. It guarantees the metadata is trustworthy in shape;
check_axioms establishes that it is trustworthy in content.

Usage:  python ci/check_status.py [ROOT=formal]
Exit:   0 pass, 1 violation, 2 usage/parse error.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

VALID_STATUS = {"formalized", "stated", "informal"}
ENTRY_REQUIRED = ("name", "citation", "area")
CLAIM_REQUIRED = ("lean_name", "status", "verified_at")
NAMESPACES = ("Konigsberg.Literature.", "Konigsberg.Areas.", "Konigsberg.Foundations.")


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        return [f"parse error: {e}"]

    entry = data.get("entry")
    if not isinstance(entry, dict):
        errors.append("missing [entry] table")
    else:
        for key in ENTRY_REQUIRED:
            if not entry.get(key):
                errors.append(f"[entry] missing '{key}'")

    claims = data.get("claims", [])
    if not claims:
        errors.append("no [[claims]] — an entry with no claims is not useful")

    for i, claim in enumerate(claims):
        loc = f"claims[{i}]"
        for key in CLAIM_REQUIRED:
            if key not in claim:
                errors.append(f"{loc} missing '{key}'")

        status = claim.get("status")
        if status not in VALID_STATUS:
            errors.append(f"{loc} invalid status {status!r} (want {sorted(VALID_STATUS)})")

        name = claim.get("lean_name", "")
        if name and not name.startswith(NAMESPACES):
            errors.append(f"{loc} lean_name {name!r} not under a Konigsberg namespace")

        if status == "formalized":
            if "axioms" not in claim:
                errors.append(f"{loc} formalized but has no 'axioms' field")
            elif "sorryAx" in claim.get("axioms", []):
                errors.append(f"{loc} formalized but records sorryAx — contradiction")

    return errors


def main(root: str = "formal") -> int:
    root_path = Path(root)
    if not root_path.exists():
        print(f"::error::root path does not exist: {root_path}")
        return 2

    total = 0
    for status_path in sorted(root_path.rglob("status.toml")):
        for err in check_file(status_path):
            print(f"::error file={status_path}::{err}")
            total += 1

    if total:
        print(f"check_status: FAIL ({total} error(s))")
        return 1
    print("check_status: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
