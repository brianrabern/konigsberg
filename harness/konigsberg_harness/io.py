"""I/O helpers: status.toml read/write, subprocess wrappers with timeouts."""
from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import Any


def read_status(path: str | Path) -> dict[str, Any]:
    return tomllib.loads(Path(path).read_text())


def write_status(path: str | Path, data: dict[str, Any]) -> None:
    import tomli_w  # deferred: keeps read path stdlib-only

    Path(path).write_text(tomli_w.dumps(data))


def run(cmd: list[str], *, timeout_s: float, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Timed, isolated subprocess. Never shell=True."""
    return subprocess.run(
        cmd, cwd=cwd, timeout=timeout_s, capture_output=True, text=True, check=False
    )
