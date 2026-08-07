"""Interactive REPL — Claude-Code-shaped session loop for graph theory.

Turn-boundary steering + Ctrl-C interrupt at event boundaries. Compaction never
touches the ledger. Mid-tool-call async injection is deferred (see Agent.step).
"""
from __future__ import annotations

import argparse
import atexit
import os
import signal
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from . import ui
from .agent import (
    Agent,
    AgentConfig,
    AssistantFinal,
    Interrupted,
)
from .compaction import CompactionConfig, compact, should_compact
from .models import AssistantText, HistoryItem, Model, Tier
from .session import SessionStore
from .tools.registry import ToolRegistry, build_registry

if TYPE_CHECKING:
    from .lean_repl import LeanREPL

# Formal tools registered only when a live LeanREPL is passed to build_registry.
_FORMAL_TOOL_NAMES = frozenset(
    {
        "lean_check",
        "lean_typecheck_statement",
        "lean_search",
        "lean_prove",
        "verify_coloring",
    }
)


def lean_toolchain_available(formal_dir: Path | None = None) -> bool:
    """True when ``formal/.lake/packages/mathlib`` exists (mirrors agent_demo)."""
    root = formal_dir or Path("formal")
    return (root / ".lake" / "packages" / "mathlib").is_dir()


def open_lean_repl(
    *, formal_dir: Path | None = None, timeout_s: float = 180
) -> LeanREPL | None:
    """Start a LeanREPL when the toolchain is present; else None (Lean-free registry).

    Does **not** load the scratch preamble here — that import can take tens of
    seconds and used to make ``uv run konigsberg`` look hung before ``kg>``.
    ``lean_prove`` / ``lean_check`` / … call ``ensure_preamble()`` on first use
    (with a one-line status print).
    """
    root = formal_dir or Path("formal")
    if not lean_toolchain_available(root):
        return None
    from .lean_repl import LeanREPL

    repl = LeanREPL(project_dir=str(root), timeout_s=timeout_s)
    repl.start()
    return repl


def formal_tier_label(registry: ToolRegistry) -> str:
    """Human-facing formal-tier status for ``/tools``."""
    names = set(registry.names())
    if _FORMAL_TOOL_NAMES <= names:
        return "formal tier: live"
    return "formal tier: unavailable (no Lean toolchain)"


def _warn_missing_runtime_deps() -> None:
    """Loud banner when SAT/CEGAR deps are absent (distinct from a tool error)."""
    try:
        from konigsberg_empirical.coloring import choosability as ch

        if not ch.is_available():
            ui.warn("TOOL UNAVAILABLE: choosability_refute — pysat not installed")
    except ImportError:
        ui.warn("TOOL UNAVAILABLE: choosability_refute — pysat not installed")


class ScriptedReplModel:
    """Offline stand-in when no API key is present."""

    def __init__(self, responses: list | None = None) -> None:
        self._q = list(responses or [])

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        if self._q:
            return self._q.pop(0)
        # Echo last user text so the REPL is usable offline without a queue.
        for item in reversed(history):
            if hasattr(item, "text"):
                return AssistantText(f"(scripted) acknowledged: {item.text[:200]}")
        return AssistantText("(scripted model idle)")


def build_model(scripted: list | None = None) -> Model:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from .models import AnthropicModel

            return AnthropicModel()
        except RuntimeError:
            pass
    return ScriptedReplModel(scripted)


# Back-compat for tests that patch/call the old renderer name.
def _render_event(event: object) -> None:
    ui.render_event(event, ui.Spinner())


SLASH_HELP = """\
Slash commands:
  /help              this help
  /tools             registered model-callable tools (+ formal tier status)
  /ledger            claims + trust roots
  /compact           force context compaction (ledger untouched)
  /clear             start a fresh session
  /save              flush note (sessions auto-persist)
  /resume [id]       load a session by id
  /sessions          list session ids
  /quit              exit
"""


class Repl:
    def __init__(
        self,
        *,
        store: SessionStore | None = None,
        registry: ToolRegistry | None = None,
        model: Model | None = None,
        compaction: CompactionConfig | None = None,
        lean_repl: LeanREPL | None = None,
    ) -> None:
        self.store = store or SessionStore()
        self.lean_repl = lean_repl
        self.registry = registry or build_registry(lean_repl)
        self.model = model or build_model()
        self.compaction = compaction or CompactionConfig()
        self.agent = Agent(self.registry, self.model, AgentConfig())
        self.session = self.store.create()

    def close(self) -> None:
        if self.lean_repl is not None:
            self.lean_repl.close()
            self.lean_repl = None

    def _maybe_auto_compact(self) -> None:
        if should_compact(self.session, self.compaction):
            ui.info("auto-compacting chat transcript (ledger untouched)")
            compact(self.session, self.model, config=self.compaction, store=self.store)

    def run_agent(self) -> None:
        """Drive Agent.step with live rendering; Ctrl-C → interrupt flag."""

        def _on_sigint(_signum, _frame):
            self.agent.request_interrupt()
            ui.warn("interrupt requested — finishing current event…")

        prev = signal.signal(signal.SIGINT, _on_sigint)
        spinner = ui.Spinner()
        try:
            for event in self.agent.step(self.session, store=self.store):
                ui.render_event(event, spinner)
                if isinstance(event, Interrupted):
                    break
            self._maybe_auto_compact()
        finally:
            spinner.stop()
            signal.signal(signal.SIGINT, prev)

    def handle_slash(self, line: str) -> bool:
        """Return True if the REPL should exit."""
        parts = line.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/quit", "/exit", "/q"):
            return True
        if cmd == "/help":
            ui.console.print(SLASH_HELP)
            return False
        if cmd == "/tools":
            ui.info(formal_tier_label(self.registry))
            for spec in self.registry.tool_specs():
                props = list((spec.get("input_schema") or {}).get("properties") or {})
                ui.console.print(f"  [kg.tool]{spec['name']}[/]  [kg.dim]args={props}[/]")
                ui.console.print(f"    [kg.dim]{spec.get('description', '')[:120]}[/]")
            code_only = [
                n
                for n in self.registry.names()
                if n not in {s["name"] for s in self.registry.tool_specs()}
            ]
            if code_only:
                ui.info(f"code-only, not model-exposed: {', '.join(code_only)}")
            return False
        if cmd == "/ledger":
            ui.render_ledger(self.session.ledger.render())
            return False
        if cmd == "/compact":
            summary = compact(
                self.session, self.model, config=self.compaction, store=self.store
            )
            ui.info("compacted")
            if summary:
                ui.console.print(summary)
            else:
                ui.info("(nothing to compact)")
            return False
        if cmd == "/clear":
            self.session = self.store.create()
            ui.info(f"new session {self.session.id}")
            return False
        if cmd == "/save":
            ui.info(
                f"session {self.session.id} auto-persists to "
                f"{self.store.path_for(self.session.id)}"
            )
            return False
        if cmd == "/sessions":
            ids = self.store.list_ids()
            ui.console.print("\n".join(ids) if ids else "(no sessions)")
            return False
        if cmd == "/resume":
            sid = arg or self.store.latest_id()
            if not sid:
                ui.info("no sessions to resume")
                return False
            try:
                self.session = self.store.load(sid)
            except FileNotFoundError as e:
                ui.warn(f"resume failed: {e}")
                return False
            ui.info(
                f"resumed {self.session.id}; "
                f"{len(self.session.history)} history items; "
                f"{len(self.session.ledger.claims())} claims"
            )
            return False
        ui.warn(f"unknown command {cmd!r} — try /help")
        return False

    def loop(self) -> int:
        ui.banner(
            self.session.id,
            formal_tier_label(self.registry),
            lean_live=self.lean_repl is not None,
            model_label=ui.model_status_label(),
        )
        first = True
        while True:
            try:
                line = ui.read_line(hint=first)
                first = False
            except EOFError:
                ui.console.print()
                return 0
            except KeyboardInterrupt:
                ui.console.print()
                ui.info("use /quit to exit, or send a message")
                continue
            if not line:
                continue
            if line.startswith("/"):
                if self.handle_slash(line):
                    return 0
                continue
            self.store.log_user(self.session, line)
            self.run_agent()


def run_headless(
    task: str,
    *,
    store: SessionStore | None = None,
    lean_repl: LeanREPL | None = None,
) -> int:
    store = store or SessionStore()
    # Caller owns lean_repl lifecycle when passed; otherwise open/close locally.
    own_repl = lean_repl is None
    repl = lean_repl if lean_repl is not None else open_lean_repl()
    if own_repl and repl is not None:
        ui.info("repl: live LeanREPL")
    elif own_repl:
        ui.info("repl: none (formal/.lake missing — empirical tools only)")
    try:
        registry = build_registry(repl)
        model = build_model()
        agent = Agent(registry, model, AgentConfig())
        session = store.create()
        result = agent.run(task, session=session, store=store)
        ui.render_ledger(result.ledger.render())
        if result.final:
            ui.render_event(
                AssistantFinal(
                    text=result.final,
                    commentary=result.commentary or "",
                ),
                ui.Spinner(),
            )
        ui.info(f"session {session.id}")
        ui.info(formal_tier_label(registry))
        return 0 if result.ledger.claims() or result.final else 1
    finally:
        if own_repl and repl is not None:
            repl.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="konigsberg",
        description="Interactive graph-theory research assistant (ledger-backed).",
    )
    parser.add_argument("--task", "-p", type=str, help="Headless one-shot task")
    parser.add_argument("--resume", type=str, metavar="ID", help="Resume session id")
    parser.add_argument(
        "--continue",
        dest="continue_latest",
        action="store_true",
        help="Resume the most recent session",
    )
    parser.add_argument(
        "--sessions-dir",
        type=Path,
        default=None,
        help="Override ~/.konigsberg/sessions",
    )
    args = parser.parse_args(argv)

    store = SessionStore(args.sessions_dir)
    _warn_missing_runtime_deps()
    lean = open_lean_repl()
    # Lean status is folded into the interactive banner; only announce for headless.
    if args.task:
        if lean is not None:
            ui.info("repl: live LeanREPL")
        else:
            ui.info("repl: none (formal/.lake missing — empirical tools only)")
        try:
            return run_headless(args.task, store=store, lean_repl=lean)
        finally:
            if lean is not None:
                lean.close()

    repl = Repl(store=store, lean_repl=lean)
    atexit.register(repl.close)
    if args.resume:
        repl.session = store.load(args.resume)
        ui.info(f"resumed {repl.session.id}")
    elif args.continue_latest:
        latest = store.latest()
        if latest is None:
            ui.info("no prior session; starting fresh")
        else:
            repl.session = latest
            ui.info(f"continued {repl.session.id}")

    try:
        return repl.loop()
    finally:
        repl.close()


if __name__ == "__main__":
    sys.exit(main())
