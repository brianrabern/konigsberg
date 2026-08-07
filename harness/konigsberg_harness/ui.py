"""Terminal chrome for the interactive REPL — Claude-Code-shaped, ledger-aware.

Minimal startup (seven-bridges mark + live health readout), a thin rule before
the prompt, and compact live tool lines. Uses Rich when stdout is a TTY.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule
from rich.status import Status
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from .agent import (
    AssistantFinal,
    ClaimMinted,
    Interrupted,
    ModelThinking,
    ToolCallProposed,
    ToolResult,
)
from .ledger import Claim

# Color means one thing at a time (Rich named colors — adapt to light/dark):
#   identity  cyan   — logo, title, prompt
#   status    green / yellow(amber) / red — health values only
#   neutral   dim    — path, session, version, labels, hints, chrome
_THEME = Theme(
    {
        "kg.brand": "bold cyan",
        "kg.dim": "dim",
        "kg.ok": "bold green",
        "kg.degraded": "bold yellow",
        "kg.err": "bold red",
        "kg.prompt": "bold cyan",
        "kg.tool": "cyan",
    }
)

_PLAIN = os.environ.get("KONIGSBERG_PLAIN", "").strip().lower() in {"1", "true", "yes"}
console = Console(
    theme=_THEME,
    highlight=False,
    force_terminal=False if _PLAIN else None,
)

# Seven bridges of Königsberg — multigraph on 4 landmasses:
#   N/S banks (deg 3), W Kneiphof island (deg 5), E eastern bank (deg 3).
# Logical bridges (7): WN, WN, NE, WE, WS, WS, SE.
_KONIGSBERG_MARK = (
    "    ●  \n"  # N
    "  ╱╱ ╲ \n"  # WN, WN, NE
    " ●────●\n"  # W —— WE —— E
    "  ╲╲ ╱ \n"  # WS, WS, SE
    "    ●  "  # S
)


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("konigsberg-harness")
    except Exception:  # noqa: BLE001 — display-only
        return "0.0.0"


def _cwd_display() -> str:
    home = Path.home()
    cwd = Path.cwd()
    try:
        return "~/" + str(cwd.relative_to(home))
    except ValueError:
        return str(cwd)


def _mark_text() -> Text:
    """Seven-bridges icon in the identity cyan (no decorative node colors)."""
    out = Text()
    for ch in _KONIGSBERG_MARK:
        if ch == "●" or ch in "╱╲─":
            out.append(ch, style="kg.brand")
        else:
            out.append(ch)
    return out


def _short_model_name(model_id: str) -> str:
    """claude-sonnet-4-5-20250929 → sonnet-4.5"""
    m = re.search(
        r"(sonnet|haiku|opus)[-_]?(\d+)[-_.]?(\d+)?",
        model_id,
        flags=re.IGNORECASE,
    )
    if not m:
        return model_id
    family = m.group(1).lower()
    major, minor = m.group(2), m.group(3) or "0"
    return f"{family}-{major}.{minor}"


def empirical_ready() -> bool:
    """True when the SAT/CEGAR stack (pysat) is importable."""
    try:
        from konigsberg_empirical.coloring import choosability as ch

        return ch.is_available()
    except ImportError:
        return False


def model_status_label() -> str:
    """Short frontier model id when live; ``offline`` when scripted / no key."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "offline"
    try:
        from .models import _default_frontier_id

        return _short_model_name(_default_frontier_id())
    except Exception:  # noqa: BLE001
        return "offline"


def _append_status(line: Text, *, label: str, glyph: str, value: str, style: str) -> None:
    """``formal: ✓ live`` — dim label, colored glyph+value (shape survives no-color)."""
    line.append(f"{label}: ", style="kg.dim")
    line.append(f"{glyph} {value}", style=style)


def health_line(*, lean_live: bool | None) -> Text:
    """Live readout of the three axes. Color = status only; glyphs backup color."""
    formal_ok = bool(lean_live)
    empiric_ok = empirical_ready()
    model = model_status_label()
    model_ok = model != "offline"

    line = Text()
    _append_status(
        line,
        label="formal",
        glyph="✓" if formal_ok else "✗",
        value="live" if formal_ok else "off",
        style="kg.ok" if formal_ok else "kg.err",
    )
    line.append(" · ", style="kg.dim")
    _append_status(
        line,
        label="empirical",
        glyph="✓" if empiric_ok else "▲",
        value="ready" if empiric_ok else "degraded",
        style="kg.ok" if empiric_ok else "kg.degraded",
    )
    line.append(" · ", style="kg.dim")
    _append_status(
        line,
        label="model",
        glyph="✓" if model_ok else "✗",
        value=model,
        style="kg.ok" if model_ok else "kg.err",
    )
    return line


@dataclass
class Spinner:
    """Tracks an optional Rich Status so ModelThinking ↔ next event stays tidy."""

    _status: Status | None = field(default=None, repr=False)

    def show(self, message: str = "Thinking…") -> None:
        if self._status is None:
            self._status = console.status(
                Text(message, style="kg.dim"),
                spinner="dots",
                spinner_style="cyan",
            )
            self._status.start()
        else:
            self._status.update(Text(message, style="kg.dim"))

    def stop(self) -> None:
        if self._status is not None:
            self._status.stop()
            self._status = None


def _truncate(s: str, n: int = 100) -> str:
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _fmt_args(args: dict) -> str:
    try:
        raw = json.dumps(args, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        raw = str(args)
    return _truncate(raw, 90)


def banner(
    session_id: str,
    formal_label: str = "",
    *,
    lean_live: bool | None = None,
    model_label: str | None = None,
) -> None:
    """Startup: seven-bridges mark + colored health readout of the three axes.

    ``formal_label`` / ``model_label`` kept for call-site compat; health is
    derived from ``lean_live`` + live pysat/API probes (not decorative tags).
    """
    _ = (formal_label, model_label)  # call-site compat; status is probed
    meta = Text()
    meta.append("Konigsberg", style="kg.brand")
    meta.append(f" v{_version()}", style="kg.dim")
    meta.append("\n")
    meta.append(_cwd_display(), style="kg.dim")
    meta.append("\n")
    meta.append(f"session {session_id[:8]}", style="kg.dim")

    grid = Table.grid(padding=(0, 3))
    grid.add_column(no_wrap=True, justify="left", vertical="middle")
    grid.add_column(no_wrap=True, justify="left", vertical="middle")
    grid.add_row(_mark_text(), meta)

    console.print()
    console.print(grid)
    # Full-width health line (avoids wrapping ``model: …`` beside the mark).
    console.print()
    console.print(health_line(lean_live=lean_live))
    console.print()


def render_event(event: object, spinner: Spinner) -> None:
    """Render one agent event; drive ``spinner`` across ModelThinking gaps."""
    if isinstance(event, ModelThinking):
        spinner.show(event.message)
        return

    spinner.stop()

    if isinstance(event, ToolCallProposed):
        c = event.call
        t = Text()
        t.append("  ⎿  ", style="kg.dim")
        t.append(c.name, style="kg.tool")
        t.append(" ", style="kg.dim")
        t.append(_fmt_args(c.args), style="kg.dim")
        console.print(t)
        spinner.show(f"Running {c.name}…")
    elif isinstance(event, ToolResult):
        if event.unavailable:
            console.print()
            console.print(Text(f"  ▲  {event.content}", style="kg.dim"))
            console.print()
        elif event.is_error:
            t = Text()
            t.append("  ⎿  ", style="kg.dim")
            t.append("✗ ", style="kg.dim")
            t.append(_truncate(event.content, 120), style="kg.dim")
            console.print(t)
        else:
            t = Text()
            t.append("  ⎿  ", style="kg.dim")
            t.append(_truncate(event.content, 120), style="kg.dim")
            console.print(t)
    elif isinstance(event, ClaimMinted):
        t = Text()
        t.append("  ★  ", style="kg.dim")
        t.append(event.claim.render(), style="kg.dim")
        console.print(t)
    elif isinstance(event, AssistantFinal):
        _render_final(event.text)
    elif isinstance(event, Interrupted):
        console.print()
        console.print(Text("interrupted — session saved", style="kg.dim"))
        console.print()


def _render_final(text: str) -> None:
    """Established / Commentary as labeled blocks (no heavy boxes)."""
    established, commentary = _split_zones(text)
    console.print()
    if established is not None:
        console.print(Text("Established", style="kg.dim"))
        for line in (established.strip() or "(nothing established)").splitlines():
            console.print(Text(f"  {line}" if line else "", style="kg.dim"))
        console.print()
        body = (commentary or "").strip()
        if body:
            console.print(Text("Commentary", style="kg.dim"))
            console.print(Markdown(body))
    else:
        console.print(Markdown(text.strip()) if text.strip() else Text(""))
    console.print()


def _split_zones(text: str) -> tuple[str | None, str | None]:
    marker_e = "Established (ledger):"
    marker_c = "Commentary:"
    if marker_e not in text or marker_c not in text:
        return None, None
    i = text.find(marker_e)
    j = text.find(marker_c)
    if i < 0 or j < 0 or j < i:
        return None, None
    established = text[i + len(marker_e) : j]
    commentary = text[j + len(marker_c) :]
    return established, commentary


def render_ledger(claims: list[Claim] | tuple[Claim, ...] | str) -> None:
    if isinstance(claims, str):
        body = claims or "(ledger empty)"
    else:
        body = "\n".join(c.render() for c in claims) if claims else "(ledger empty)"
    console.print()
    console.print(Text("Ledger", style="kg.dim"))
    for line in body.splitlines() or ["(ledger empty)"]:
        console.print(Text(f"  {line}", style="kg.dim"))
    console.print()


def info(msg: str) -> None:
    console.print(Text(msg, style="kg.dim"))


def warn(msg: str) -> None:
    # Not status-amber: warnings are chrome, not the health axis.
    console.print(Text(msg, style="kg.dim"))


def prompt_rule() -> None:
    console.print(Rule(style="dim"))


def prompt_label() -> Text:
    return Text("> ", style="kg.prompt")


def read_line(*, hint: bool = False) -> str:
    """Rule + `>` prompt; optional dim hint (Claude Code placeholder analogue)."""
    prompt_rule()
    if hint:
        console.print(Text('  Try "Is C₅ 2-choosable?" or /help', style="kg.dim"))
    return console.input(prompt_label()).strip()


def format_args_preview(args: dict[str, Any]) -> str:
    return _fmt_args(args)
