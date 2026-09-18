"""REPL UI chrome: zone split + event rendering (plain mode, no TTY needed)."""
from __future__ import annotations

import os

os.environ["KONIGSBERG_PLAIN"] = "1"

from konigsberg_harness.agent import (
    AssistantFinal,
    ClaimMinted,
    ModelThinking,
    ToolCallProposed,
    ToolResult,
)
from konigsberg_harness.ledger import mint_conjecture
from konigsberg_harness.models import ToolCall
from konigsberg_harness.ui import Spinner, _split_zones, render_event


def test_split_zones_parses_grounded_answer():
    text = (
        "Established (ledger):\n"
        "[proved] foo\n\n"
        "Commentary:\n"
        "bar baz"
    )
    est, defs, refs, com = _split_zones(text)
    assert est is not None and "foo" in est
    assert defs is None
    assert refs is None
    assert com is not None and "bar baz" in com.strip()


def test_split_zones_with_references():
    text = (
        "Established (ledger):\n"
        "(nothing established)\n\n"
        "References (corpus):\n"
        "RabernBook — formalized (in-tree)\n\n"
        "Commentary:\n"
        "see above"
    )
    est, defs, refs, com = _split_zones(text)
    assert est is not None and "nothing established" in est
    assert defs is None
    assert refs is not None and "RabernBook" in refs
    assert com is not None and "see above" in com.strip()


def test_split_zones_with_definition():
    text = (
        "Established (ledger):\n"
        "[certificate-checked] C~ IS 4-list-critical\n\n"
        "Definition used:\n"
        "4-list-critical = not 3-choosable, edge-minimal [Cranston–Rabern]\n\n"
        "Commentary:\n"
        "yes"
    )
    est, defs, refs, com = _split_zones(text)
    assert est is not None and "4-list-critical" in est
    assert defs is not None and "not 3-choosable" in defs
    assert refs is None
    assert com is not None and "yes" in com.strip()


def test_render_event_thinking_and_tool(capsys):
    spinner = Spinner()
    render_event(ModelThinking("Thinking…"), spinner)
    assert spinner._status is not None
    render_event(
        ToolCallProposed(ToolCall(id="1", name="alon_tarsi", args={"graph6": "Bg"})),
        spinner,
    )
    out = capsys.readouterr().out
    assert "alon_tarsi" in out
    render_event(
        ToolResult(
            call=ToolCall(id="1", name="alon_tarsi", args={}),
            content="[certificate-checked] ok",
        ),
        spinner,
    )
    claim = mint_conjecture("hunch")
    render_event(ClaimMinted(claim), spinner)
    out = capsys.readouterr().out
    assert "hunch" in out or "conjectured" in out
    spinner.stop()


def test_banner_includes_konigsberg_bridges_mark(capsys):
    from konigsberg_harness.ui import banner

    banner(
        "abcdef12deadbeef",
        lean_live=True,
    )
    out = capsys.readouterr().out
    assert "●" in out
    assert "Konigsberg" in out
    assert "session abcdef12" in out
    assert "formal:" in out
    assert "live" in out
    assert "empirical:" in out
    assert "model:" in out


def test_konigsberg_mark_has_seven_bridges():
    """Topology: WN×2, NE, WE, WS×2, SE — 4 nodes, double arcs only on the west."""
    from konigsberg_harness.ui import _KONIGSBERG_MARK

    assert _KONIGSBERG_MARK.count("●") == 4
    # Diagonal bridges only (WE is the horizontal span).
    assert _KONIGSBERG_MARK.count("╱") == 3  # WN, WN, SE
    assert _KONIGSBERG_MARK.count("╲") == 3  # NE, WS, WS
    assert "─" in _KONIGSBERG_MARK  # WE
    # Double west arcs present; no triple (that was the 9-bridge bug).
    assert "╱╱" in _KONIGSBERG_MARK and "╲╲" in _KONIGSBERG_MARK
    assert "╱╱╱" not in _KONIGSBERG_MARK and "╲╲╲" not in _KONIGSBERG_MARK


def test_model_status_label_local(monkeypatch):
    from konigsberg_harness.ui import model_status_label

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("KONIGSBERG_PROVIDER", "local")
    monkeypatch.setenv("KONIGSBERG_MODEL", "Qwen2.5-Coder-32B-Instruct")
    assert model_status_label() == "Qwen2.5-Coder-32B-Instruct"
    from konigsberg_harness.ui import _short_model_name, health_line

    assert _short_model_name("claude-sonnet-4-5-20250929") == "sonnet-4.5"
    assert _short_model_name("claude-haiku-4-5-20251001") == "haiku-4.5"
    assert (
        _short_model_name("/models/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf")
        == "Qwen2.5-Coder-32B-Instruct-Q4_K_M"
    )
    live = health_line(lean_live=True)
    plain = live.plain
    assert "formal: ✓ live" in plain
    assert "empirical:" in plain
    assert "enum:" in plain
    assert "✓" in plain or "▲" in plain
    assert "model:" in plain
    offline = health_line(lean_live=False)
    assert "formal: ✗ off" in offline.plain
    assert "atlas≤7" in offline.plain or "geng" in offline.plain


def test_render_final_panels(capsys):
    spinner = Spinner()
    render_event(
        AssistantFinal(
            text=(
                "Established (ledger):\n"
                "[proved] thing\n\n"
                "Commentary:\n"
                "Just prose."
            ),
            commentary="Just prose.",
        ),
        spinner,
    )
    out = capsys.readouterr().out
    assert "Established" in out
    assert "Commentary" in out
    assert "Just prose" in out
