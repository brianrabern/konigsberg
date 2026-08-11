#!/usr/bin/env python3
"""check_imports — every Konigsberg/*.lean module reachable from the root.

An orphan file still compiles under the lake glob, but escapes axiom / sorry
gates that only see what the root transitively imports. Fail loudly on orphans
and on root imports that point at missing files.

Usage:  python ci/check_imports.py [ROOT=formal]
Exit:   0 pass, 1 violation, 2 usage error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

IMPORT_RE = re.compile(r"^import\s+(Konigsberg(?:\.[A-Za-z0-9_]+)+)\s*$")


def module_of(lean_file: Path, konigsberg_dir: Path) -> str:
    rel = lean_file.relative_to(konigsberg_dir).with_suffix("")
    return "Konigsberg." + ".".join(rel.parts)


def file_of(module: str, konigsberg_dir: Path) -> Path:
    parts = module.split(".")
    assert parts[0] == "Konigsberg"
    return konigsberg_dir.joinpath(*parts[1:]).with_suffix(".lean")


def parse_imports(lean_file: Path) -> list[str]:
    out: list[str] = []
    for line in lean_file.read_text().splitlines():
        code = line.split("--", 1)[0].strip()
        m = IMPORT_RE.match(code)
        if m:
            out.append(m.group(1))
    return out


def reachable(root_file: Path, konigsberg_dir: Path) -> set[str]:
    seen: set[str] = set()
    stack = ["Konigsberg"]
    while stack:
        mod = stack.pop()
        if mod in seen:
            continue
        seen.add(mod)
        path = root_file if mod == "Konigsberg" else file_of(mod, konigsberg_dir)
        if not path.exists():
            continue
        for dep in parse_imports(path):
            if dep not in seen:
                stack.append(dep)
    return seen


def main(root: str = "formal") -> int:
    root_path = Path(root)
    konigsberg_dir = root_path / "Konigsberg"
    root_file = root_path / "Konigsberg.lean"
    if not root_file.exists() or not konigsberg_dir.is_dir():
        print(f"::error::expected {root_file} and {konigsberg_dir}/")
        return 2

    found = reachable(root_file, konigsberg_dir)
    violations = 0

    for lean in sorted(konigsberg_dir.rglob("*.lean")):
        mod = module_of(lean, konigsberg_dir)
        if mod not in found:
            print(f"::error file={lean}::not reachable from Konigsberg.lean (import {mod})")
            violations += 1

    # Reverse: root-reachable Konigsberg.* modules must exist on disk.
    for mod in sorted(found):
        if mod == "Konigsberg":
            continue
        path = file_of(mod, konigsberg_dir)
        if not path.exists():
            print(f"::error file={root_file}::imports {mod} but {path} does not exist")
            violations += 1

    if violations:
        print(f"check_imports: FAIL ({violations} violation(s))")
        return 1
    print(f"check_imports: OK ({len(found)} module(s) reachable)")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
