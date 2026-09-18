"""Interactive REPL — Claude-Code-shaped session loop for graph theory.

Turn-boundary steering + Ctrl-C interrupt at event boundaries. Compaction never
touches the ledger. Mid-tool-call async injection is deferred (see Agent.step).
"""
from __future__ import annotations

import argparse
import atexit
import os
import re
import signal
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from . import ui
from .agent import (
    BK_CAMPAIGN_TASK,
    FOREVER_KICKOFF,
    HUNT_KICKOFF,
    Agent,
    AgentConfig,
    AssistantFinal,
    ClaimMinted,
    HuntContinued,
    Interrupted,
    ToolResult,
    _hunt_kickoff_text,
    _seed_user_message,
)
from .compaction import CompactionConfig, compact, should_compact
from .grounding import (
    MISSION_BK,
    MISSION_HITTING,
    MISSION_REED,
    build_system_prompt,
)
from .lemmas import LemmaNotebook, replay_locked_lemmas
from .models import AssistantText, HistoryItem, Model, Tier, UserMsg
from .session import Session, SessionStore
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
        "lean_add_to_library",
        "lemma_list",
        "lemma_read",
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
    """Loud banner when SAT/CEGAR or enumeration deps are absent."""
    try:
        from konigsberg_empirical.coloring import choosability as ch

        if not ch.is_available():
            ui.warn("TOOL UNAVAILABLE: choosability_refute — pysat not installed")
    except ImportError:
        ui.warn("TOOL UNAVAILABLE: choosability_refute — pysat not installed")
    try:
        from konigsberg_empirical.search.enumerate import _find_geng

        if _find_geng() is None:
            ui.warn(
                "geng not on PATH — bk_search / enumeration n>7 need nauty "
                "(run: make deps)"
            )
    except ImportError:
        pass


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


_MISSIONS: dict[str, str] = {
    "bk": MISSION_BK,
    "reed": MISSION_REED,
    "hitting": MISSION_HITTING,
}


def apply_mission(model: object, mission: str) -> bool:
    """Point a model at a mission by rebuilding its system prompt.

    No-op-safe for the offline scripted model (which has no ``system_prompt``).
    Returns True when the mission was applied to a live model.
    """
    block = _MISSIONS.get(mission.lower())
    if block is None or not hasattr(model, "system_prompt"):
        return False
    model.system_prompt = build_system_prompt(mission=block)
    return True


def build_model(scripted: list | None = None, *, mission: str = "bk") -> Model:
    model: Model
    try:
        from .models import build_live_model

        model = build_live_model()
    except RuntimeError:
        model = ScriptedReplModel(scripted)
    apply_mission(model, mission)
    return model


# Back-compat for tests that patch/call the old renderer name.
def _render_event(event: object) -> None:
    ui.render_event(event, ui.Spinner())


SLASH_HELP = """\
Slash commands:
  /help              this help
  /tools             registered model-callable tools (+ formal tier status)
  /model [spec]      show or set the chat model (opus, local GGUF name, …)
  /mission [name]    show or set the research mission (bk, reed, hitting)
  /ledger            claims + trust roots
  /claim [n]         render claim n (1-based) verbatim from the ledger; omit n for latest
  /referee [n]       adversarial review of claim n (default: latest proved)
  /promote [n]       referee + (on accept) human-confirmed Literature write-back
  /lemmas            locked proofs this investigation (working notebook)
  /hunt [task]       autonomous loop until lean_prove succeeds (not chat)
  /forever           BK campaign: loop until the conjecture is proved or disproved
  /reset             drop session Lean decls; replay locked lemmas on clean preamble
  /compact           force context compaction (ledger untouched)
  /clear             start a fresh session
  /save              flush note (sessions auto-persist)
  /resume [id]       load a session by id
  /sessions          list session ids
  /quit              exit

/model usage:
  /model                 show current chat model
  /model list            short-name catalog (Claude aliases, or local ids)
  /model opus            switch chat model to Opus 5 (Anthropic)
  /model opus 4.8        switch to Opus 4.8
  /model claude-opus-5   full API id also fine
  /model <gguf-name>     llama.cpp / OpenAI-compat: any id the server accepts
"""

# Display-only asks — answer from the ledger, do not call the model.
_CLAIM_DISPLAY_RE = re.compile(
    r"(?is)^\s*(please\s+)?(show|display|echo|print|repeat)\s+"
    r"(me\s+)?(the\s+)?(certificate|claim|ledger\s+claim)s?\b"
)


class Repl:
    def __init__(
        self,
        *,
        store: SessionStore | None = None,
        registry: ToolRegistry | None = None,
        model: Model | None = None,
        compaction: CompactionConfig | None = None,
        lean_repl: LeanREPL | None = None,
        mission: str = "bk",
    ) -> None:
        self.store = store or SessionStore()
        self.lean_repl = lean_repl
        self.notebook = LemmaNotebook()
        self.registry = registry or build_registry(lean_repl, notebook=self.notebook)
        self.model = model or build_model(mission=mission)
        self.mission = mission if mission in _MISSIONS else "bk"
        apply_mission(self.model, self.mission)
        if compaction is not None:
            self.compaction = compaction
        else:
            from .models import live_provider

            raw_thresh = os.environ.get("KONIGSBERG_COMPACT_THRESHOLD", "").strip()
            if raw_thresh:
                self.compaction = CompactionConfig(threshold=int(raw_thresh))
            elif live_provider() == "openai":
                # 32k-class local GGUFs fill up faster than Claude's 80k default.
                self.compaction = CompactionConfig(threshold=20_000)
            else:
                self.compaction = CompactionConfig()
        self.agent = Agent(
            self.registry,
            self.model,
            AgentConfig(compaction=self.compaction),
        )
        self.session = self.store.create()
        self.session.notebook = self.notebook
        self._last_referee_report = None  # RefereeReport | None
        self._pending_promote: dict | None = None

    def bind_session(self, session: Session) -> None:
        """Point the REPL at a loaded session, sharing the working notebook."""
        self.notebook.replace(list(session.notebook.lemmas))
        session.notebook = self.notebook
        self.session = session
        if self.lean_repl is not None and self.notebook.lemmas:
            ok, errors = replay_locked_lemmas(self.lean_repl, self.notebook)
            ui.info(f"replayed {ok}/{len(self.notebook.lemmas)} locked lemmas")
            for err in errors[:5]:
                ui.warn(err)

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
        proved_this_turn = False
        try:
            for event in self.agent.step(self.session, store=self.store):
                ui.render_event(event, spinner)
                if isinstance(event, Interrupted):
                    break
                if isinstance(event, HuntContinued):
                    proved_this_turn = False
                if isinstance(event, ClaimMinted) and event.claim.provenance.label() in (
                    "proved",
                    "proved-mod-axioms",
                ):
                    proved_this_turn = True
            self._maybe_auto_compact()
            if proved_this_turn:
                ui.info("proved Claim minted — run the referee on this? (`/referee`)")
        finally:
            spinner.stop()
            signal.signal(signal.SIGINT, prev)

    def _run_hunt(
        self, task: str, *, forever: bool = False, kickoff: str | None = None
    ) -> None:
        """Autonomous loop. ``forever`` stops only if BK is proved or disproved."""
        prev = self.agent.config
        self.agent.config = AgentConfig(
            hunt=True,
            hunt_forever=forever,
            hunt_max_rounds=0 if forever else prev.hunt_max_rounds,
            hunt_require_durable=prev.hunt_require_durable,
            compaction=self.compaction,
        )
        try:
            text = kickoff or (FOREVER_KICKOFF if forever else HUNT_KICKOFF)
            self.store.log_user(self.session, f"{task}\n\n{text}")
            if forever:
                ui.info(
                    "BK campaign — looping until the conjecture is proved or "
                    "disproved (Ctrl-C also stops); lemmas lock and the hunt continues"
                )
            else:
                ui.info("hunt mode — Ctrl-C interrupts; loop continues until lean_prove")
            self.run_agent()
        finally:
            self.agent.config = prev

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
            for category, specs in self.registry.grouped_tool_specs():
                ui.console.print(f"  [kg.accent]{category}[/]")
                for spec in specs:
                    props = list(
                        (spec.get("input_schema") or {}).get("properties") or {}
                    )
                    ui.console.print(
                        f"    [kg.tool]{spec['name']}[/]  [kg.dim]args={props}[/]"
                    )
                    ui.console.print(
                        f"      [kg.dim]{spec.get('description', '')[:120]}[/]"
                    )
            code_only = [
                n
                for n in self.registry.names()
                if n not in {s["name"] for s in self.registry.tool_specs()}
            ]
            if code_only:
                ui.info(f"code-only, not model-exposed: {', '.join(code_only)}")
            return False
        if cmd == "/model":
            self._handle_model_cmd(arg)
            return False
        if cmd == "/mission":
            self._handle_mission_cmd(arg)
            return False
        if cmd == "/ledger":
            ui.render_ledger(self.session.ledger.render())
            return False
        if cmd == "/claim":
            self._render_claim(arg)
            return False
        if cmd == "/referee":
            self._handle_referee(arg)
            return False
        if cmd == "/promote":
            self._handle_promote(arg)
            return False
        if cmd == "/reset":
            if self.lean_repl is None:
                ui.warn("formal tier unavailable — nothing to reset")
                return False
            try:
                from .tools.lean_tools import reset_env

                msg = reset_env(self.lean_repl, self.notebook)
                ui.info(msg)
            except Exception as e:  # noqa: BLE001
                ui.warn(f"reset failed: {type(e).__name__}: {e}")
            return False
        if cmd == "/lemmas":
            ui.info(self.notebook.list_render())
            return False
        if cmd == "/hunt":
            task = arg.strip()
            if not task:
                ui.warn("/hunt needs a goal — e.g. /hunt theorem foo : True := by trivial")
                return False
            self._run_hunt(task)
            return False
        if cmd == "/forever":
            from .models import has_live_provider

            if not has_live_provider():
                ui.warn(
                    "BK campaign needs a live model "
                    "(OPENAI_BASE_URL / KONIGSBERG_PROVIDER=local, or ANTHROPIC_API_KEY)"
                )
                return False
            task = arg.strip() or BK_CAMPAIGN_TASK
            self._run_hunt(task, forever=True)
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
            self.notebook.clear()
            self.session = self.store.create()
            self.session.notebook = self.notebook
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
                loaded = self.store.load(sid)
            except FileNotFoundError as e:
                ui.warn(f"resume failed: {e}")
                return False
            self.bind_session(loaded)
            ui.info(
                f"resumed {self.session.id}; "
                f"{len(self.session.history)} history items; "
                f"{len(self.session.ledger.claims())} claims; "
                f"{len(self.notebook.lemmas)} locked lemmas"
            )
            return False
        ui.warn(f"unknown command {cmd!r} — try /help")
        return False

    def _handle_model_cmd(self, arg: str) -> None:
        """``/model`` — show or set the chat model (agent frontier id)."""
        return self._model_cmd_body(arg)

    def _handle_mission_cmd(self, arg: str) -> None:
        """``/mission`` — show or set the research mission (bk, reed)."""
        avail = ", ".join(sorted(_MISSIONS))
        key = arg.strip().lower()
        if not key:
            ui.info(f"mission: {self.mission}  (available: {avail})")
            return
        if key not in _MISSIONS:
            ui.warn(f"unknown mission {arg!r} — available: {avail}")
            return
        if apply_mission(self.model, key):
            self.mission = key
            ui.info(f"mission → {key}")
        else:
            ui.warn(
                "mission switching needs a live model "
                "(OPENAI_BASE_URL or ANTHROPIC_API_KEY)"
            )

    def _model_cmd_body(self, arg: str) -> None:
        from .model_catalog import format_model_catalog
        from .models import Tier, is_live_model, model_provider_kind

        m = self.model
        if not is_live_model(m):
            ui.warn(
                "model switching needs a live model "
                "(OPENAI_BASE_URL / KONIGSBERG_PROVIDER=local, or ANTHROPIC_API_KEY)"
            )
            return

        raw = arg.strip()
        kind = model_provider_kind(m) or "anthropic"
        if not raw:
            ui.info(f"chat model: {m.frontier_model_id}")
            if kind == "openai":
                ui.info("try: /model list | /model <server-model-id>")
            else:
                ui.info("try: /model opus | /model opus 4.8 | /model list")
            return
        if raw.lower() in {"list", "ls", "aliases"}:
            ui.console.print(format_model_catalog(provider=kind))
            return

        # Optional advanced: `/model cheap haiku` for compaction-only model.
        parts = raw.split(maxsplit=1)
        head = parts[0].lower()
        if head == "cheap":
            if len(parts) < 2:
                ui.warn("/model cheap needs a name — e.g. /model cheap haiku")
                return
            try:
                mid = m.set_model_id(Tier.CHEAP, parts[1])
            except ValueError as e:
                ui.warn(str(e))
                return
            ui.info(f"compaction model → {mid}")
            return
        if head == "frontier" and len(parts) == 2:
            raw = parts[1]

        try:
            mid = m.set_model_id(Tier.FRONTIER, raw)
        except ValueError as e:
            ui.warn(str(e))
            return
        ui.info(f"chat model → {mid}")

    def _resolve_claim(self, arg: str = "", *, prefer_proved: bool = False):
        """Return (1-based index, Claim) or None."""
        claims = self.session.ledger.claims()
        if not claims:
            ui.info("ledger empty — nothing to review")
            return None
        if arg.strip():
            try:
                idx = int(arg.strip())
            except ValueError:
                ui.warn(f"expected a 1-based claim index, got {arg!r}")
                return None
            if idx < 1 or idx > len(claims):
                ui.warn(f"claim {idx} out of range (1..{len(claims)})")
                return None
            return idx, claims[idx - 1]
        if prefer_proved:
            for i in range(len(claims), 0, -1):
                if claims[i - 1].provenance.label() in ("proved", "proved-mod-axioms"):
                    return i, claims[i - 1]
        return len(claims), claims[-1]

    def _run_referee_on_claim(self, claim):
        """Run referee with adversarial pass when a live model is present; fail-closed."""
        from .models import has_live_provider
        from .referee import build_referee_model, run_referee

        ledger = self.session.ledger.claims()
        if has_live_provider() and hasattr(self.model, "system_prompt"):
            try:
                return run_referee(
                    claim,
                    registry=self.registry,
                    model=build_referee_model(),
                    ledger_claims=ledger,
                    repl=self.lean_repl,
                )
            except Exception as e:  # noqa: BLE001
                from .referee import RefereeReport

                return RefereeReport(
                    recommendation="unavailable",
                    major_issues=(f"adversarial referee failed: {e}",),
                    claim_statement=claim.statement,
                    review_unavailable_reason=str(e),
                )
        return run_referee(
            claim,
            registry=self.registry,
            ledger_claims=ledger,
            repl=self.lean_repl,
        )

    def _handle_referee(self, arg: str) -> None:
        """``/referee [n]`` — adversarial review (or heuristic-only if no key)."""
        resolved = self._resolve_claim(arg, prefer_proved=True)
        if resolved is None:
            return
        idx, claim = resolved
        ui.info(f"refereeing claim {idx}: {claim.render()[:120]}…")
        report = self._run_referee_on_claim(claim)
        self._last_referee_report = report
        ui.console.print()
        ui.console.print("[kg.accent]Referee report[/]")
        ui.console.print(report.render())
        ui.console.print()
        if report.allows_promotion():
            ui.info("recommendation: accept — run /promote to write back (human confirm)")
        elif report.recommendation == "unavailable":
            ui.warn("REFEREE UNAVAILABLE — not vetted; promotion blocked")
        elif report.recommendation == "no-automated-issues":
            ui.warn(
                "heuristic checks only — NOT adversarially reviewed; promotion blocked"
            )
        else:
            ui.warn(
                f"recommendation: {report.recommendation} — promotion blocked "
                "while Major issues stand"
            )

    def _handle_promote(self, arg: str) -> None:
        """``/promote [n]`` — referee then (on accept + confirm) lean_add_to_library."""
        from .tools.library_writeback import LibraryWriteError, lean_add_to_library

        resolved = self._resolve_claim(arg, prefer_proved=True)
        if resolved is None:
            return
        idx, claim = resolved
        ui.info(f"promote pipeline on claim {idx}")
        if not claim.provenance.durable:
            ui.warn(
                "promotion blocked — claim is [session-only]; assemble a single "
                "self-contained snippet and lean_prove(..., durable=True)"
            )
            return
        report = self._run_referee_on_claim(claim)
        self._last_referee_report = report
        ui.console.print(report.render())
        if not report.allows_promotion():
            if report.recommendation == "unavailable":
                ui.warn("REFEREE UNAVAILABLE — not vetted; promotion blocked")
            elif report.recommendation == "no-automated-issues":
                ui.warn(
                    "promotion blocked — configure a live model "
                    "(OPENAI_BASE_URL or ANTHROPIC_API_KEY) and re-run /referee "
                    "for adversarial review"
                )
            else:
                ui.warn("promotion blocked — fix Major issues / revise, then /referee again")
            if report.suggested_revision:
                ui.info(f"suggested revision: {report.suggested_revision}")
            return
        if self.lean_repl is None:
            ui.warn("formal tier unavailable — cannot lean_add_to_library without Lean")
            return

        # Collect write-back fields interactively.
        ui.info("referee accepted. Enter write-back fields (empty cancels).")
        lean_name = input("lean_name> ").strip()
        if not lean_name:
            ui.info("cancelled")
            return
        snippet = input("snippet path (.lean file)> ").strip()
        # For v1: require a file path containing the Lean snippet.
        if not snippet:
            ui.warn("provide a path to a .lean snippet file for this promotion")
            return
        from pathlib import Path

        path = Path(snippet).expanduser()
        if not path.is_file():
            ui.warn(f"snippet file not found: {path}")
            return
        lean_src = path.read_text(encoding="utf-8")
        citation = input("citation> ").strip() or "session promotion"
        informal = input("informal_statement> ").strip() or claim.statement
        area = input("area [coloring]> ").strip() or "coloring"
        sanity_path = input("sanity_snippet path (required)> ").strip()
        if not sanity_path:
            ui.warn("SanityChecks snippet required")
            return
        sanity = Path(sanity_path).expanduser().read_text(encoding="utf-8")

        ui.console.print("[kg.accent]About to write Literature entry[/]")
        ui.console.print(f"  lean_name: {lean_name}")
        ui.console.print(f"  area: {area}")
        ui.console.print(f"  citation: {citation}")
        ui.console.print(f"  referee: {report.recommendation}")
        confirm = input("Promote to corpus? [y/N]> ").strip().lower()
        if confirm not in ("y", "yes"):
            ui.info("cancelled — corpus unchanged")
            return
        try:
            minted = lean_add_to_library(
                self.lean_repl,
                lean_name,
                lean_src,
                area=area,
                citation=citation,
                informal_statement=informal,
                referee_report=report,
                sanity_snippet=sanity,
                confirmed=True,
                source_claim=claim,
            )
        except LibraryWriteError as e:
            ui.warn(f"write-back refused: {e}")
            return
        except Exception as e:  # noqa: BLE001
            ui.warn(f"write-back failed: {type(e).__name__}: {e}")
            return
        self.session.ledger.record(minted)
        self.store.log_claim(self.session, minted)
        ui.info(minted.render())
        ui.info("corpus updated — run `make gates` before pushing")

    def _render_claim(self, arg: str = "") -> None:
        """Print one ledger Claim verbatim (1-based index; default = latest)."""
        claims = self.session.ledger.claims()
        if not claims:
            ui.info("ledger empty — nothing to show")
            return
        if arg.strip():
            try:
                idx = int(arg.strip())
            except ValueError:
                ui.warn(f"/claim expects a 1-based index, got {arg!r}")
                return
            if idx < 1 or idx > len(claims):
                ui.warn(f"/claim {idx} out of range (1..{len(claims)})")
                return
            claim = claims[idx - 1]
            label = f"claim {idx}/{len(claims)}"
        else:
            claim = claims[-1]
            label = f"claim {len(claims)}/{len(claims)} (latest)"
        ui.console.print()
        ui.console.print(f"[kg.dim]{label}[/]")
        ui.render_ledger(claim.render())
        ui.console.print()

    def _try_claim_display(self, line: str) -> bool:
        """If the user asked to show a stored certificate, render from ledger."""
        if not _CLAIM_DISPLAY_RE.match(line.strip()):
            return False
        self._render_claim("")
        return True

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
            try:
                if line.startswith("/"):
                    if self.handle_slash(line):
                        return 0
                    continue
                if self._try_claim_display(line):
                    self.store.log_user(self.session, line)
                    continue
                self.store.log_user(self.session, line)
                self.run_agent()
            except KeyboardInterrupt:
                ui.console.print()
                ui.info("interrupted — back to the prompt")
            except Exception as e:  # noqa: BLE001 — one bad turn must not end the session
                ui.warn(
                    f"error this turn ({type(e).__name__}: {e}) — "
                    "session preserved, continuing"
                )


def run_headless(
    task: str,
    *,
    store: SessionStore | None = None,
    lean_repl: LeanREPL | None = None,
    mission: str = "bk",
    hunt: bool = False,
    hunt_require_durable: bool = False,
    hunt_max_rounds: int = 200,
    hunt_forever: bool = False,
    session: Session | None = None,
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
        notebook = LemmaNotebook()
        if session is not None:
            notebook.replace(list(session.notebook.lemmas))
            session.notebook = notebook
        registry = build_registry(repl, notebook=notebook)
        if repl is not None and notebook.lemmas:
            ok, errors = replay_locked_lemmas(repl, notebook)
            ui.info(f"replayed {ok}/{len(notebook.lemmas)} locked lemmas")
            for err in errors[:5]:
                ui.warn(err)
        from .models import live_provider

        raw_thresh = os.environ.get("KONIGSBERG_COMPACT_THRESHOLD", "").strip()
        if raw_thresh:
            compaction = CompactionConfig(threshold=int(raw_thresh))
        elif live_provider() == "openai":
            compaction = CompactionConfig(threshold=20_000)
        else:
            compaction = CompactionConfig()
        hunt = hunt or hunt_forever
        model = build_model(mission=mission)
        agent = Agent(
            registry,
            model,
            AgentConfig(
                hunt=hunt,
                hunt_forever=hunt_forever,
                hunt_require_durable=hunt_require_durable,
                hunt_max_rounds=hunt_max_rounds,
                compaction=compaction,
            ),
        )
        sess = session or store.create()
        sess.notebook = notebook
        if hunt_forever:
            ui.info(
                "BK campaign — looping until the conjecture is proved or "
                "disproved (Ctrl-C also stops); lemmas lock and the hunt continues"
            )
        elif hunt:
            ui.info("hunt mode — looping until lean_prove (Ctrl-C interrupts)")
        seed = (
            UserMsg(f"{task}\n\n{_hunt_kickoff_text(agent.config)}")
            if hunt
            else _seed_user_message(task)
        )
        store.log_user(sess, seed.text)

        spinner = ui.Spinner()
        final: str | None = None
        had_tools = False

        def _on_sigint(_signum, _frame):
            agent.request_interrupt()
            ui.warn("interrupt requested — finishing current event…")

        prev_sig = signal.signal(signal.SIGINT, _on_sigint)
        try:
            for event in agent.step(sess, store=store):
                ui.render_event(event, spinner)
                if isinstance(event, AssistantFinal):
                    final = event.text
                elif isinstance(event, ToolResult):
                    had_tools = True
                elif isinstance(event, Interrupted):
                    break
        finally:
            spinner.stop()
            signal.signal(signal.SIGINT, prev_sig)

        ui.render_ledger(sess.ledger.render())
        if hunt and agent.config.hunt_max_rounds > 0:
            cap = agent.config.hunt_max_rounds
            if agent._rounds >= cap and not final:
                ui.info(f"round cap reached ({agent._rounds}/{cap})")
        if sess.notebook.lemmas:
            ui.info(f"locked lemmas: {sess.notebook.list_render()}")
        ui.info(f"session {sess.id}")
        ui.info(formal_tier_label(registry))
        return 0 if sess.ledger.claims() or final or had_tools else 1
    finally:
        if own_repl and repl is not None:
            repl.close()


def main(argv: list[str] | None = None) -> int:
    from .envfile import load_project_env

    # Fill os.environ from repo-root .env (gitignored). Does not override exports.
    load_project_env()

    parser = argparse.ArgumentParser(
        prog=Path(sys.argv[0]).name if argv is None else "konigsberg",
        description="Interactive graph-theory research assistant (ledger-backed).",
    )
    parser.add_argument("--task", "-p", type=str, help="Headless one-shot task")
    parser.add_argument(
        "--until-proved",
        action="store_true",
        help="Autonomous hunt: loop until lean_prove succeeds (not chat)",
    )
    parser.add_argument(
        "--forever",
        action="store_true",
        help="BK campaign: loop until the conjecture is proved or disproved",
    )
    parser.add_argument(
        "--require-durable",
        action="store_true",
        help="With --until-proved, only stop on durable=True proofs",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        metavar="N",
        help="Hunt round cap (default 200 for --until-proved, unlimited for --forever; 0 = unlimited)",
    )
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
    parser.add_argument(
        "--mission",
        type=str,
        default="bk",
        choices=sorted(_MISSIONS),
        help="Research mission the agent is pointed at (default: bk)",
    )
    args = parser.parse_args(argv)
    if (
        args.until_proved
        and not args.forever
        and not args.task
        and not (args.continue_latest or args.resume)
    ):
        parser.error("--until-proved requires --task, or --continue/--resume")
    if args.forever:
        from .models import has_live_provider

        if not has_live_provider():
            ui.warn(
                "BK campaign needs a live model "
                "(OPENAI_BASE_URL / KONIGSBERG_PROVIDER=local, or ANTHROPIC_API_KEY)"
            )
            return 1

    store = SessionStore(args.sessions_dir)
    _warn_missing_runtime_deps()
    lean = open_lean_repl()
    hunt_session = None
    if args.resume:
        hunt_session = store.load(args.resume)
    elif args.continue_latest and (args.until_proved or args.forever):
        hunt_session = store.latest()

    if args.forever:
        max_rounds = 0 if args.max_rounds is None else args.max_rounds
        task = args.task or BK_CAMPAIGN_TASK
    elif args.until_proved:
        max_rounds = 200 if args.max_rounds is None else args.max_rounds
        task = args.task or "Continue the hunt until a lemma or theorem is kernel-checked."
    else:
        max_rounds = 200 if args.max_rounds is None else args.max_rounds
        task = args.task

    # Lean status is folded into the interactive banner; only announce for headless.
    if args.until_proved or args.forever or args.task:
        if lean is not None:
            ui.info("repl: live LeanREPL")
        else:
            ui.info("repl: none (formal/.lake missing — empirical tools only)")
        try:
            return run_headless(
                task,
                store=store,
                lean_repl=lean,
                mission=args.mission,
                hunt=bool(args.until_proved or args.forever),
                hunt_forever=bool(args.forever),
                hunt_require_durable=bool(args.require_durable),
                hunt_max_rounds=max_rounds,
                session=hunt_session,
            )
        finally:
            if lean is not None:
                lean.close()

    repl = Repl(store=store, lean_repl=lean, mission=args.mission)
    atexit.register(repl.close)
    if args.resume:
        repl.bind_session(store.load(args.resume))
        ui.info(f"resumed {repl.session.id}")
    elif args.continue_latest:
        latest = store.latest()
        if latest is None:
            ui.info("no prior session; starting fresh")
        else:
            repl.bind_session(latest)
            ui.info(f"continued {repl.session.id}")

    try:
        return repl.loop()
    finally:
        repl.close()


if __name__ == "__main__":
    sys.exit(main())
