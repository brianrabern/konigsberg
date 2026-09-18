"""Tests for repo-root .env loading."""

from __future__ import annotations

import os
from pathlib import Path

from konigsberg_harness.envfile import _parse_line, load_project_env


def test_parse_line_strips_quotes_and_export() -> None:
    assert _parse_line("ANTHROPIC_API_KEY='sk-test'") == ("ANTHROPIC_API_KEY", "sk-test")
    assert _parse_line('export FOO="bar"') == ("FOO", "bar")
    assert _parse_line("# comment") is None
    assert _parse_line("") is None


def test_load_project_env_does_not_override(tmp_path: Path, monkeypatch) -> None:
    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_CHEAP_MODEL=from-file\nKEEP_ME=file\n")
    monkeypatch.setattr(
        "konigsberg_harness.envfile._repo_root_candidates",
        lambda: [tmp_path],
    )
    monkeypatch.setenv("ANTHROPIC_CHEAP_MODEL", "from-shell")
    monkeypatch.delenv("KEEP_ME", raising=False)

    loaded = load_project_env(override=False)
    assert loaded == env.resolve()
    assert os.environ["ANTHROPIC_CHEAP_MODEL"] == "from-shell"
    assert os.environ["KEEP_ME"] == "file"
