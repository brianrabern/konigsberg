#!/usr/bin/env python3
"""Ensure runtime deps: Python workspace + system nauty (geng).

Python packages come from ``uv sync``. Nauty is a system binary — not on PyPI —
so this script installs it via the platform package manager when missing.

Idempotent. Non-interactive by default (``--yes`` implied for brew/apt when
``KONIGSBERG_DEPS_YES=1`` or ``--yes``). Without ``--yes``, prints the command
to run rather than sudo/brew-mutating.

Usage:
  uv run python scripts/ensure_deps.py --yes
  make deps
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENG_CANDIDATES = ("geng", "nauty-geng")


def _have_geng() -> str | None:
    for name in GENG_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    return None


def _run(cmd: list[str], *, check: bool = True) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def ensure_python(*, yes: bool) -> None:
    uv = shutil.which("uv")
    if uv is None:
        print("ERROR: uv not on PATH — install https://docs.astral.sh/uv/", file=sys.stderr)
        sys.exit(2)
    # Always sync; editable workspace + pysat/rich/etc.
    _run([uv, "sync"])


def _install_nauty_cmd() -> list[str] | None:
    if sys.platform == "darwin" and shutil.which("brew"):
        return ["brew", "install", "nauty"]
    if shutil.which("apt-get"):
        # Debian packages the binary as nauty-geng; our finder accepts that name.
        return ["sudo", "apt-get", "install", "-y", "nauty"]
    if shutil.which("dnf"):
        return ["sudo", "dnf", "install", "-y", "nauty"]
    if shutil.which("pacman"):
        return ["sudo", "pacman", "-S", "--noconfirm", "nauty"]
    return None


def ensure_nauty(*, yes: bool) -> None:
    found = _have_geng()
    if found:
        print(f"nauty/geng: ok ({found})")
        return
    cmd = _install_nauty_cmd()
    if cmd is None:
        print(
            "ERROR: geng not on PATH and no supported package manager found.\n"
            "  Install nauty manually, then ensure `geng` or `nauty-geng` is on PATH.\n"
            "  macOS: brew install nauty\n"
            "  Debian/Ubuntu: sudo apt-get install nauty\n"
            "  Or build from https://pallini.di.uniroma1.it/",
            file=sys.stderr,
        )
        sys.exit(1)
    if not yes and not os.environ.get("KONIGSBERG_DEPS_YES"):
        print(f"nauty/geng: missing — run: {' '.join(cmd)}")
        print("(re-run with --yes or KONIGSBERG_DEPS_YES=1 to install automatically)")
        sys.exit(1)
    rc = _run(cmd)
    if rc != 0:
        sys.exit(rc)
    found = _have_geng()
    if not found:
        print(
            "ERROR: nauty install finished but geng/nauty-geng still not on PATH",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"nauty/geng: ok ({found})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="install missing system packages without prompting",
    )
    ap.add_argument(
        "--skip-python",
        action="store_true",
        help="only check/install nauty",
    )
    ap.add_argument(
        "--skip-nauty",
        action="store_true",
        help="only uv sync",
    )
    args = ap.parse_args(argv)
    if not args.skip_python:
        ensure_python(yes=args.yes)
    if not args.skip_nauty:
        ensure_nauty(yes=args.yes)
    print("deps: ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
