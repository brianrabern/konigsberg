"""Load repo-root ``.env`` into ``os.environ`` for local runs.

Keys are still read via ``os.environ`` (never constructor args). This only
fills the environment from a gitignored ``.env`` so ``uv run konigsberg``
works without a manual ``source .env``. Existing variables are not overridden.
"""

from __future__ import annotations

import os
from pathlib import Path


def _repo_root_candidates() -> list[Path]:
    """Cwd ancestry (prefer a tree that looks like this repo) + package root."""
    out: list[Path] = []
    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        out.append(p)
        if (p / "formal" / "lakefile.toml").is_file() and (p / "harness").is_dir():
            break
    # harness/konigsberg_harness/envfile.py → parents[2] == repo root when editable
    out.append(Path(__file__).resolve().parents[2])
    return out


def find_dotenv() -> Path | None:
    seen: set[Path] = set()
    for root in _repo_root_candidates():
        path = (root / ".env").resolve()
        if path in seen:
            continue
        seen.add(path)
        if path.is_file():
            return path
    return None


def _parse_line(line: str) -> tuple[str, str] | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if s.startswith("export "):
        s = s[len("export ") :].strip()
    if "=" not in s:
        return None
    key, _, raw = s.partition("=")
    key = key.strip()
    if not key:
        return None
    val = raw.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in {'"', "'"}:
        val = val[1:-1]
    return key, val


def load_project_env(*, override: bool = False) -> Path | None:
    """Load ``.env`` into ``os.environ``. Returns the path loaded, or ``None``."""
    path = find_dotenv()
    if path is None:
        return None
    for line in path.read_text().splitlines():
        parsed = _parse_line(line)
        if parsed is None:
            continue
        key, val = parsed
        if override or key not in os.environ:
            os.environ[key] = val
    return path
