"""Tests for Anthropic model alias resolution."""

from __future__ import annotations

import pytest
from konigsberg_harness.model_catalog import format_model_catalog, resolve_model_id


@pytest.mark.parametrize(
    ("spec", "want"),
    [
        ("opus", "claude-opus-5"),
        ("opus 5", "claude-opus-5"),
        ("opus 4.8", "claude-opus-4-8"),
        ("opus-4.8", "claude-opus-4-8"),
        ("sonnet", "claude-sonnet-5"),
        ("fable", "claude-fable-5"),
        ("haiku", "claude-haiku-4-5"),
        ("claude-opus-5", "claude-opus-5"),
        ("claude-sonnet-4-6", "claude-sonnet-4-6"),
    ],
)
def test_resolve_model_id(spec: str, want: str) -> None:
    assert resolve_model_id(spec) == want


def test_resolve_unknown_alias() -> None:
    with pytest.raises(ValueError, match="unknown model"):
        resolve_model_id("gpt-4o")


def test_resolve_local_passthrough() -> None:
    assert (
        resolve_model_id("Qwen2.5-Coder-32B-Instruct", provider="openai")
        == "Qwen2.5-Coder-32B-Instruct"
    )
    assert resolve_model_id("local", provider="local") == "local"


def test_format_local_catalog() -> None:
    text = format_model_catalog(provider="openai")
    assert "llama.cpp" in text
    assert "KONIGSBERG_MODEL" in text
