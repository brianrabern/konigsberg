"""Terminal chrome for the interactive REPL — Claude-Code-shaped, ledger-aware.

Minimal startup (seven-bridges mark + live health readout), a thin rule before
the prompt, and compact live tool lines. Uses Rich when stdout is a TTY.
"""
from __future__ import annotations

import itertools
import json
import os
import re
import sys
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
    HuntContinued,
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
    """claude-sonnet-4-5-20250929 → sonnet-4.5; GGUF paths → basename."""
    m = re.search(
        r"(sonnet|haiku|opus)[-_]?(\d+)[-_.]?(\d+)?",
        model_id,
        flags=re.IGNORECASE,
    )
    if m:
        family = m.group(1).lower()
        major, minor = m.group(2), m.group(3) or "0"
        return f"{family}-{major}.{minor}"
    name = Path(model_id).name.removesuffix(".gguf")
    return name[:40] if len(name) > 40 else name


def empirical_ready() -> bool:
    """True when the SAT/CEGAR stack (pysat) is importable."""
    try:
        from konigsberg_empirical.coloring import choosability as ch

        return ch.is_available()
    except ImportError:
        return False


def geng_ready() -> bool:
    """True when nauty ``geng`` / ``nauty-geng`` is on PATH (n>7 enumeration)."""
    try:
        from konigsberg_empirical.search.enumerate import _find_geng

        return _find_geng() is not None
    except ImportError:
        return False


def model_status_label() -> str:
    """Short frontier model id when live; ``offline`` when scripted / no provider."""
    try:
        from .models import default_frontier_id, live_provider

        if live_provider() is None:
            return "offline"
        return _short_model_name(default_frontier_id())
    except Exception:  # noqa: BLE001
        return "offline"


def _append_status(line: Text, *, label: str, glyph: str, value: str, style: str) -> None:
    """``formal: ✓ live`` — dim label, colored glyph+value (shape survives no-color)."""
    line.append(f"{label}: ", style="kg.dim")
    line.append(f"{glyph} {value}", style=style)


def health_line(*, lean_live: bool | None) -> Text:
    """Live readout of the axes. Color = status only; glyphs backup color."""
    formal_ok = bool(lean_live)
    empiric_ok = empirical_ready()
    enum_ok = geng_ready()
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
        label="enum",
        glyph="✓" if enum_ok else "▲",
        value="geng" if enum_ok else "atlas≤7",
        style="kg.ok" if enum_ok else "kg.degraded",
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


# Contextual status verbs — one per tool so the spinner names the actual activity
# ("Contracting…" while taking a minor), plus a rotation for pure reasoning turns.
_TOOL_VERBS: dict[str, str] = {
    # construction / io
    "make_graph": "Constructing", "graph6_encode": "Encoding", "graph6_decode": "Decoding",
    # inspection / basic getters
    "describe_graph": "Inspecting",
    "order": "Getting", "size": "Getting", "degree_sequence": "Getting",
    "min_degree": "Getting", "average_degree": "Getting", "max_degree": "Getting",
    "neighbors": "Getting",
    # connectivity / measures / checks / counts
    "is_connected": "Probing", "num_components": "Probing", "components": "Probing",
    "vertex_connectivity": "Probing", "edge_connectivity": "Probing",
    "is_k_connected": "Probing",
    "girth": "Measuring", "diameter": "Measuring", "radius": "Measuring",
    "eccentricity": "Measuring",
    "is_bipartite": "Checking", "is_tree": "Checking", "is_forest": "Checking",
    "is_regular": "Checking", "is_planar": "Checking", "is_eulerian": "Checking",
    "has_eulerian_path": "Checking",
    "triangle_count": "Counting", "transitivity": "Counting",
    "degeneracy": "Peeling", "k_core_number": "Peeling", "k_core": "Peeling",
    "independence_number": "Packing", "matching_number": "Matching",
    "clique_number": "Searching",
    # structural transforms
    "complement": "Complementing",
    "induced_subgraph": "Pruning", "delete_vertex": "Pruning",
    "delete_vertices": "Pruning", "delete_edge": "Pruning", "delete_edges": "Pruning",
    "add_edge": "Adding", "add_vertex": "Adding",
    "contract_edge": "Contracting", "contains_minor": "Contracting",
    "line_graph": "Transforming",
    "disjoint_union": "Combining", "union": "Combining", "join": "Combining",
    "cartesian_product": "Combining", "tensor_product": "Combining",
    # relations
    "is_isomorphic": "Matching", "could_be_isomorphic": "Matching",
    "is_subgraph": "Embedding", "is_induced_subgraph": "Embedding",
    "contains_clique": "Searching", "contains_cycle": "Searching",
    "contains_path": "Searching",
    # paths / traversal
    "distance": "Walking", "shortest_path": "Walking",
    "bfs_order": "Traversing", "dfs_order": "Traversing", "spanning_tree": "Spanning",
    # generators / search
    "enumerate_graphs": "Enumerating", "random_graph": "Sampling",
    "bk_search": "Hunting", "counterexample_search": "Hunting",
    # coloring / choosability
    "choosability_refute": "Refuting", "alon_tarsi": "Orienting",
    "fixer_breaker": "Playing", "decide_colorable": "Coloring",
    "chromatic_number": "Bounding", "bk_predicate": "Testing",
    "list_critical": "Testing", "verify_coloring": "Certifying",
    "reducible_configuration": "Reducing",
    "discharging_unavoidable": "Discharging",
    "campaign_status": "Reviewing",
    # formal
    "lean_check": "Checking", "lean_typecheck_statement": "Checking",
    "lean_search": "Searching", "lean_prove": "Proving",
    "lean_add_to_library": "Promoting",
    "lemma_list": "Recalling", "lemma_read": "Recalling",
    "reset_env": "Resetting", "retract": "Retracting",
    # literature
    "literature_search": "Combing", "arxiv_search": "Combing",
}

# Rotation for reasoning turns (when the model emits the default "Thinking…").
_THINKING_VERBS = (
    "Thinking…", "Reasoning…", "Pondering…", "Conjecturing…",
    "Connecting…", "Chasing…", "Circling…", "Musing…",
)
_thinking_cycle = itertools.cycle(_THINKING_VERBS)


def verb_for_tool(name: str) -> str:
    """Contextual spinner label for a tool call, e.g. 'Contracting…'."""
    return f"{_TOOL_VERBS.get(name, 'Computing')}…"


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
        # Rotate through research verbs on a plain reasoning turn; honor a
        # specific message if the agent set one.
        msg = next(_thinking_cycle) if event.message == "Thinking…" else event.message
        spinner.show(msg)
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
        spinner.show(verb_for_tool(c.name))
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
    elif isinstance(event, HuntContinued):
        t = Text()
        t.append("  hunt  ", style="kg.dim")
        t.append("continuing (no lean_prove yet)", style="kg.dim")
        console.print(t)
        spinner.show("Hunting…")


def _render_final(text: str) -> None:
    """Established / Definition / References / Commentary as labeled blocks."""
    established, definitions, references, commentary = _split_zones(text)
    console.print()
    if established is not None:
        console.print(Text("Established", style="kg.dim"))
        for line in (established.strip() or "(nothing established)").splitlines():
            console.print(Text(f"  {line}" if line else "", style="kg.dim"))
        console.print()
        if definitions is not None and definitions.strip():
            console.print(Text("Definition used", style="kg.dim"))
            for line in definitions.strip().splitlines():
                console.print(Text(f"  {line}" if line else "", style="kg.dim"))
            console.print()
        if references is not None and references.strip():
            console.print(Text("References", style="kg.dim"))
            for line in references.strip().splitlines():
                console.print(Text(f"  {line}" if line else "", style="kg.dim"))
            console.print()
        body = (commentary or "").strip()
        if body:
            console.print(Text("Commentary", style="kg.dim"))
            console.print(Markdown(body))
    else:
        console.print(Markdown(text.strip()) if text.strip() else Text(""))
    console.print()


def _split_zones(
    text: str,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Parse harness zones. Zone headers must be line-initial (not inside a Claim)."""
    marker_e = "Established (ledger):"
    marker_c = "Commentary:"
    if marker_e not in text or marker_c not in text:
        return None, None, None, None
    i = text.find(marker_e)
    j = text.find(marker_c)
    if i < 0 or j < 0 or j < i:
        return None, None, None, None

    mid = text[i + len(marker_e) : j]
    # Line-initial zone headers only — Claims must not embed these phrases.
    def_m = re.search(r"(?m)^Definition used:\s*$", mid)
    ref_m = re.search(r"(?m)^References \(corpus\):\s*$", mid)

    definitions = None
    references = None
    if def_m and (ref_m is None or def_m.start() < ref_m.start()):
        established = mid[: def_m.start()]
        rest = mid[def_m.end() :]
        ref2 = re.search(r"(?m)^References \(corpus\):\s*$", rest)
        if ref2:
            definitions = rest[: ref2.start()]
            references = rest[ref2.end() :]
        else:
            definitions = rest
    elif ref_m:
        established = mid[: ref_m.start()]
        references = mid[ref_m.end() :]
    else:
        established = mid
    commentary = text[j + len(marker_c) :]
    return established, definitions, references, commentary


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


def _harden_stdin() -> None:
    """Tolerate non-UTF-8 stdin bytes (odd pastes/locales) so a bad keystroke
    can't crash the whole REPL. Undecodable bytes become U+FFFD, not an exception."""
    try:  # pragma: no cover - depends on the runtime stream type
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError, OSError):
        pass


_harden_stdin()


def read_line(*, hint: bool = False) -> str:
    """Rule + `>` prompt; optional dim hint (Claude Code placeholder analogue).

    A single undecodable line is skipped, never fatal — a bad paste shouldn't end
    the session.
    """
    prompt_rule()
    if hint:
        console.print(Text('  Try "Is C₅ 2-choosable?" or /help', style="kg.dim"))
    try:
        return console.input(prompt_label()).strip()
    except UnicodeDecodeError:
        warn("input had bytes I couldn't decode — line skipped, try again")
        return ""


def format_args_preview(args: dict[str, Any]) -> str:
    return _fmt_args(args)
