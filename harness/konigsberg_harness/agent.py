"""The agent loop.

Deliberately a simple while-loop over a rich tool registry. No orchestration
graphs, no multi-agent architecture in v1 (add only when measurably justified).

The loop closes on *context assembly*: each ``step`` rebuilds the model context
from ``session.history`` + tool schemas, calls ``model.respond``, and yields
events as they happen so a REPL can render/steer live.

Trust invariant: only a tool-minted ``Claim`` enters the ledger; an
``AssistantFinal`` mints nothing. Final answers are rendered in Established
(ledger) vs Commentary (model prose) zones — see ``grounding``.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from pydantic import ValidationError

from .grounding import format_grounded_answer
from .ledger import Claim, Ledger
from .models import (
    AssistantText,
    Model,
    Tier,
    ToolCall,
    ToolResultMsg,
    UserMsg,
)
from .session import Session, SessionStore
from .tools.errors import ToolUnavailable
from .tools.registry import ToolRegistry


@dataclass
class AgentConfig:
    max_steps: int = 40


@dataclass
class Observation:
    """One tool observation (headless transcript compatibility)."""

    action: object
    result: str
    is_error: bool = False
    unavailable: bool = False


@dataclass
class AgentResult:
    final: str | None
    ledger: Ledger
    steps: int
    transcript: list[Observation] = field(default_factory=list)
    session: Session | None = None
    commentary: str | None = None


# --- Live events (REPL renders these) -------------------------------------


@dataclass(frozen=True)
class ModelThinking:
    """Emitted immediately before a model.respond call so the REPL can spin."""

    message: str = "Thinking…"


@dataclass(frozen=True)
class ToolCallProposed:
    call: ToolCall


@dataclass(frozen=True)
class ToolResult:
    call: ToolCall
    content: str
    is_error: bool = False
    unavailable: bool = False


@dataclass(frozen=True)
class ClaimMinted:
    claim: Claim


@dataclass(frozen=True)
class AssistantFinal:
    """Final answer: ``text`` is the zone render; ``commentary`` is raw prose."""

    text: str
    commentary: str
    claims: tuple[Claim, ...] = ()
    failures: tuple[str, ...] = ()
    references: tuple[dict, ...] = ()


@dataclass(frozen=True)
class Interrupted:
    """Emitted when ``request_interrupt`` was set; session left consistent."""


AgentEvent = (
    ModelThinking
    | ToolCallProposed
    | ToolResult
    | ClaimMinted
    | AssistantFinal
    | Interrupted
)


def _render_result(result: object) -> str:
    if isinstance(result, list):
        return "results: " + ("; ".join(map(str, result)) if result else "(none)")
    return str(result)


def _claims_from_result(result: object) -> list[Claim] | None:
    """Extract minted Claims from a tool result (single or bundle)."""
    if isinstance(result, Claim):
        return [result]
    if (
        isinstance(result, (list, tuple))
        and result
        and all(isinstance(c, Claim) for c in result)
    ):
        return list(result)
    return None


def _literature_hits_from_result(result: object) -> list[dict] | None:
    """Detect literature_search hit dicts (status-bearing; not Claims)."""
    if not isinstance(result, list) or not result:
        return None
    if all(
        isinstance(d, dict) and "status" in d and "lean_name" in d and "name" in d
        for d in result
    ):
        return list(result)
    return None


def _seed_user_message(task: str) -> UserMsg:
    return UserMsg(
        f"{task}\n\n"
        "Use the available tools to make progress. When finished, reply with a "
        "short plain-text summary (no tool call). Mathematical verdicts must be "
        "backed by ledger Claims from tools; if a tool fails, report not established."
    )


class Agent:
    def __init__(
        self, registry: ToolRegistry, model: Model, config: AgentConfig | None = None
    ) -> None:
        self.registry = registry
        self.model = model
        self.ledger = Ledger()  # last-run mirror for callers that still read it
        self.config = config or AgentConfig()
        self._interrupt = False
        self._rounds = 0

    def request_interrupt(self) -> None:
        """Ask ``step`` to halt at the next event boundary (Ctrl-C path)."""
        self._interrupt = True

    def clear_interrupt(self) -> None:
        self._interrupt = False

    def _persist_item(
        self, session: Session, item: object, store: SessionStore | None
    ) -> None:
        if store is not None:
            store.log_history_item(session, item)  # type: ignore[arg-type]
        else:
            session.history.append(item)  # type: ignore[arg-type]
            session.touch()

    def _persist_claim(
        self, session: Session, claim: Claim, store: SessionStore | None
    ) -> None:
        if store is not None:
            store.log_claim(session, claim)
        else:
            session.ledger.record(claim)
            session.touch()

    def step(
        self,
        session: Session,
        *,
        store: SessionStore | None = None,
        tier: Tier = Tier.FRONTIER,
    ) -> Iterator[AgentEvent]:
        """Drive until AssistantFinal, interrupt, or max_steps.

        Re-assembles context from ``session.history`` each model call. Yields
        events as tool calls/results/claims happen so the REPL can render live.

        # Mid-tool-call injection (Claude Code async dual-buffer) deferred — v1
        # steering is interrupt-at-event-boundary + turn-boundary user messages.
        """
        self.clear_interrupt()
        self._rounds = 0
        tools = self.registry.tool_specs()
        turn_claims: list[Claim] = []
        turn_failures: list[str] = []
        turn_refs: list[dict] = []

        for _ in range(self.config.max_steps):
            if self._interrupt:
                yield Interrupted()
                return

            self._rounds += 1
            yield ModelThinking("Thinking…")
            turn = self.model.respond(session.history, tools, tier=tier)

            if isinstance(turn, AssistantText):
                self._persist_item(session, turn, store)
                grounded = format_grounded_answer(
                    commentary=turn.text,
                    claims=turn_claims,
                    failures=turn_failures,
                    references=turn_refs,
                )
                yield AssistantFinal(
                    text=grounded,
                    commentary=turn.text,
                    claims=tuple(turn_claims),
                    failures=tuple(turn_failures),
                    references=tuple(turn_refs),
                )
                return

            # Record the whole assistant tool-use turn first (API requires matching
            # tool_results before the next respond).
            unanswered = list(turn)
            for call in turn:
                self._persist_item(session, call, store)
                yield ToolCallProposed(call)
                if self._interrupt:
                    for rest in unanswered:
                        tr = ToolResultMsg(
                            id=rest.id,
                            content="ERROR Interrupted",
                            is_error=True,
                        )
                        self._persist_item(session, tr, store)
                        yield ToolResult(call=rest, content=tr.content, is_error=True)
                    yield Interrupted()
                    return

            for call in turn:
                unanswered = [c for c in unanswered if c.id != call.id]
                try:
                    result = self.registry.dispatch(call.name, call.args)
                except ToolUnavailable as e:
                    banner = e.banner()
                    turn_failures.append(e.tool)
                    tr = ToolResultMsg(id=call.id, content=banner, is_error=True)
                    self._persist_item(session, tr, store)
                    yield ToolResult(
                        call=call, content=banner, is_error=True, unavailable=True
                    )
                    if self._interrupt:
                        for rest in unanswered:
                            tr = ToolResultMsg(
                                id=rest.id,
                                content="ERROR Interrupted",
                                is_error=True,
                            )
                            self._persist_item(session, tr, store)
                            yield ToolResult(call=rest, content=tr.content, is_error=True)
                        yield Interrupted()
                        return
                    continue
                except (ValidationError, Exception) as e:  # noqa: BLE001
                    err = f"ERROR {type(e).__name__}: {e}"
                    turn_failures.append(call.name)
                    tr = ToolResultMsg(id=call.id, content=err, is_error=True)
                    self._persist_item(session, tr, store)
                    yield ToolResult(call=call, content=err, is_error=True)
                    if self._interrupt:
                        for rest in unanswered:
                            tr = ToolResultMsg(
                                id=rest.id,
                                content="ERROR Interrupted",
                                is_error=True,
                            )
                            self._persist_item(session, tr, store)
                            yield ToolResult(call=rest, content=tr.content, is_error=True)
                        yield Interrupted()
                        return
                    continue

                claims = _claims_from_result(result)
                if claims is not None:
                    for claim in claims:
                        self._persist_claim(session, claim, store)
                        turn_claims.append(claim)
                    rendered = (
                        claims[0].render()
                        if len(claims) == 1
                        else "\n".join(c.render() for c in claims)
                    )
                    tr = ToolResultMsg(id=call.id, content=rendered)
                    self._persist_item(session, tr, store)
                    yield ToolResult(call=call, content=rendered, is_error=False)
                    for claim in claims:
                        yield ClaimMinted(claim)
                else:
                    lit_hits = _literature_hits_from_result(result)
                    if lit_hits is not None:
                        turn_refs.extend(lit_hits)
                    rendered = _render_result(result)
                    tr = ToolResultMsg(id=call.id, content=rendered)
                    self._persist_item(session, tr, store)
                    yield ToolResult(call=call, content=rendered, is_error=False)

                if self._interrupt:
                    for rest in unanswered:
                        tr = ToolResultMsg(
                            id=rest.id,
                            content="ERROR Interrupted",
                            is_error=True,
                        )
                        self._persist_item(session, tr, store)
                        yield ToolResult(call=rest, content=tr.content, is_error=True)
                    yield Interrupted()
                    return

        # Hit max_steps without a final text turn.
        return

    def run(
        self,
        task: str,
        *,
        session: Session | None = None,
        store: SessionStore | None = None,
    ) -> AgentResult:
        """Headless one-shot: seed a user message, drain ``step``, return result."""
        sess = session or Session.create()
        if store is not None and not store.path_for(sess.id).exists():
            store.create(sess)
        if store is not None:
            store.log_user(sess, _seed_user_message(task).text)
        else:
            sess.history.append(_seed_user_message(task))

        transcript: list[Observation] = []
        final: str | None = None
        commentary: str | None = None

        for event in self.step(sess, store=store):
            if isinstance(event, AssistantFinal):
                final = event.text
                commentary = event.commentary
            elif isinstance(event, ToolResult):
                transcript.append(
                    Observation(
                        event.call,
                        event.content,
                        is_error=event.is_error,
                        unavailable=event.unavailable,
                    )
                )
            elif isinstance(event, Interrupted):
                break

        self.ledger = sess.ledger
        return AgentResult(
            final=final,
            ledger=sess.ledger,
            steps=self._rounds,
            transcript=transcript,
            session=sess,
            commentary=commentary,
        )
