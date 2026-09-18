"""Answer grounding + pysat runtime: WP1/WP2 from docs/handoff/ANSWER_GROUNDING.md."""
from __future__ import annotations

from konigsberg_harness.agent import Agent, AgentConfig, AssistantFinal, ToolResult
from konigsberg_harness.grounding import (
    GROUNDING_SYSTEM_PROMPT,
    format_established_zone,
    format_grounded_answer,
)
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall
from konigsberg_harness.session import SessionStore
from konigsberg_harness.tools.errors import ToolUnavailable
from konigsberg_harness.tools.registry import ToolRegistry
from pydantic import BaseModel


def test_pysat_importable_in_runtime_env():
    """WP1: python-sat is a hard dep — the REPL env must import pysat."""
    import pysat  # noqa: F401
    from konigsberg_empirical.coloring import choosability as ch

    assert ch.is_available()


def test_tool_unavailable_banner_is_loud(capsys, tmp_path):
    """WP1: missing-dep failure renders as TOOL UNAVAILABLE, not a plain ERR line."""
    from konigsberg_harness.repl import Repl, ScriptedReplModel, _render_event

    class _Args(BaseModel):
        graph6: str
        k: int = 2

    reg = ToolRegistry()

    def boom(graph6: str, k: int = 2):
        raise ToolUnavailable("choosability_refute", "pysat not installed")

    reg.register("choosability_refute", boom, "doc", args_model=_Args)
    model = ScriptedReplModel(
        [
            [
                ToolCall(
                    id="1",
                    name="choosability_refute",
                    args={"graph6": "Dhc", "k": 2},
                )
            ],
            AssistantText("C5 is not 2-choosable"),  # fabricated — ledger empty
        ]
    )
    store = SessionStore(tmp_path)
    repl = Repl(store=store, registry=reg, model=model)
    store.log_user(repl.session, "Is C5 2-choosable?")

    events = list(repl.agent.step(repl.session, store=store))
    unavailable = [e for e in events if isinstance(e, ToolResult) and e.unavailable]
    assert len(unavailable) == 1
    assert unavailable[0].content.startswith("TOOL UNAVAILABLE: choosability_refute")

    _render_event(unavailable[0])
    out = capsys.readouterr().out
    assert "TOOL UNAVAILABLE" in out
    assert "▲" in out or "⚠" in out


def test_c5_grounding_regression_established_zone_not_fabricated(tmp_path):
    """WP2 load-bearing: tool errors + lying final → Established says not established.

    Encodes the live failure: choosability_refute failed, model asserted
    "C₅ is not 2-choosable" with a fake certificate — ledger stayed empty, but
    prose looked like a result. The Established zone must contradict that.
    """

    class _Args(BaseModel):
        graph6: str
        k: int = 2

    reg = ToolRegistry()

    def boom(graph6: str, k: int = 2):
        raise ToolUnavailable("choosability_refute", "pysat not installed")

    reg.register("choosability_refute", boom, "doc", args_model=_Args)

    class ScriptedModel:
        def __init__(self, responses: list):
            self._responses = list(responses)

        def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
            return self._responses.pop(0)

    lying = (
        "No, C₅ is not 2-choosable. Bad list assignment: "
        "[{0,1},{0,1},{0,1},{0,1},{0,1}] — wait, let me recalculate…"
    )
    model = ScriptedModel(
        [
            [
                ToolCall(
                    id="1",
                    name="choosability_refute",
                    args={"graph6": "Dhc", "k": 2},
                )
            ],
            AssistantText(lying),
        ]
    )
    result = Agent(reg, model, AgentConfig()).run("Is the cycle C5 2-choosable?")

    # (i) ledger empty — no claim for the fabricated verdict
    assert result.ledger.claims() == ()
    assert result.commentary == lying

    # (ii) Established zone reports not established; names the failed tool
    assert result.final is not None
    assert result.final.startswith("Established (ledger):")
    assert "nothing established" in result.final
    assert "choosability_refute" in result.final
    assert "Commentary:" in result.final
    assert lying in result.final


def test_grounding_system_prompt_states_hard_rules():
    assert "Do not state mathematical verdicts" in GROUNDING_SYSTEM_PROMPT
    assert "not established" in GROUNDING_SYSTEM_PROMPT
    assert "Never exhibit a certificate" in GROUNDING_SYSTEM_PROMPT
    assert "commentary prose only" in GROUNDING_SYSTEM_PROMPT
    assert "Do not restate established results" in GROUNDING_SYSTEM_PROMPT
    assert 'bare "/ledger"' in GROUNDING_SYSTEM_PROMPT
    assert "Ambiguity resolution" in GROUNDING_SYSTEM_PROMPT
    assert "Never silently pick one interpretation" in GROUNDING_SYSTEM_PROMPT
    assert "exactly one clarifying question" in GROUNDING_SYSTEM_PROMPT
    assert "anti-flailing" in GROUNDING_SYSTEM_PROMPT or "Open problems" in GROUNDING_SYSTEM_PROMPT
    assert "bk_search" in GROUNDING_SYSTEM_PROMPT
    assert "bk_predicate" in GROUNDING_SYSTEM_PROMPT
    assert "literature_search" in GROUNDING_SYSTEM_PROMPT
    assert "Build on Rabern" in GROUNDING_SYSTEM_PROMPT
    assert "arxiv_search" in GROUNDING_SYSTEM_PROMPT
    assert "stated only" in GROUNDING_SYSTEM_PROMPT
    assert "Never present a catalogued item as established" in GROUNDING_SYSTEM_PROMPT or (
        "Never present a catalogued or arXiv item as established" in GROUNDING_SYSTEM_PROMPT
    )
    assert "Definition grounding" in GROUNDING_SYSTEM_PROMPT
    assert "list_critical" in GROUNDING_SYSTEM_PROMPT
    assert "Never guess a parameterization" in GROUNDING_SYSTEM_PROMPT
    assert "Do not restate or regenerate certificates" in GROUNDING_SYSTEM_PROMPT
    assert "/claim" in GROUNDING_SYSTEM_PROMPT
    assert "make_graph" in GROUNDING_SYSTEM_PROMPT
    assert "describe_graph" in GROUNDING_SYSTEM_PROMPT
    assert "never write a graph6" in GROUNDING_SYSTEM_PROMPT.lower() or (
        "never write a graph6 string" in GROUNDING_SYSTEM_PROMPT
    )
    assert "Proxy inferences" in GROUNDING_SYSTEM_PROMPT
    assert "contains_minor" in GROUNDING_SYSTEM_PROMPT
    assert "is_subgraph is not a proxy" in GROUNDING_SYSTEM_PROMPT
    text = format_grounded_answer(
        commentary="yes",
        claims=(),
        definitions=[
            "4-list-critical = not 3-choosable, edge-minimal [Cranston–Rabern; Lean KListCritical / EdgeKListCritical]"
        ],
    )
    assert "Definition used:" in text
    assert "not 3-choosable" in text
    assert text.index("Established") < text.index("Definition used")
    assert text.index("Definition used") < text.index("Commentary")
    hits = [
        {
            "name": "RabernBook_FirstListBound",
            "citation": "x",
            "area": "coloring",
            "lean_name": "Konigsberg.Literature.Coloring.RabernBook_FirstListBound.firstListBound",
            "status": "stated",
            "provenance": "verified_at=abc",
        }
    ]
    text = format_grounded_answer(commentary="note", claims=(), references=hits)
    assert "References (corpus):" in text
    assert "stated only — not yet proven" in text
    # stated must not look proved
    assert "formalized (in-tree)" not in text.split("References (corpus):")[1].split("Commentary:")[0]


def test_commentary_prose_only_strips_shadow_established_and_ledger():
    from konigsberg_harness.grounding import commentary_prose_only

    raw = """\
---

## **Established**

1. **C₅ is NOT 2-choosable** (certificate-checked).
   Bad list: `[[0, 1], [0, 1]]`

## **Commentary**

The 5-cycle separates choosability from chromatic number.

---

## **/ledger**

| Claim | Type |
|-------|------|
| C₅ not 2-choosable | certificate-checked |
"""
    prose = commentary_prose_only(raw)
    assert "Established" not in prose
    assert "/ledger" not in prose
    assert "|" not in prose  # no table
    assert "separates choosability" in prose


def test_commentary_prose_only_strips_bare_definition_used():
    from konigsberg_harness.grounding import commentary_prose_only

    raw = (
        "Definition used:\n"
        "4-list-critical = not 3-choosable, edge-minimal [Cranston–Rabern]\n\n"
        "Yes. K₄ is 4-list-critical under that convention."
    )
    prose = commentary_prose_only(raw)
    assert "Definition used" not in prose
    assert "Yes. K₄ is 4-list-critical" in prose


def test_format_established_empty_with_failures():
    body = format_established_zone([], ["choosability_refute"])
    assert "nothing established" in body
    assert "choosability_refute" in body


def test_format_grounded_answer_two_zones():
    text = format_grounded_answer(commentary="maybe", claims=(), failures=["t"])
    assert "Established (ledger):" in text
    assert "Commentary:" in text
    assert "maybe" in text


def test_format_grounded_answer_uses_prose_only_commentary():
    raw = "## Established\nsecret claim\n\n## Commentary\nJust prose.\n"
    text = format_grounded_answer(commentary=raw, claims=(), failures=[])
    # Outer harness zones remain; model-emulated Established body is gone.
    assert text.count("Established (ledger):") == 1
    assert "secret claim" not in text
    assert "Just prose." in text


def test_anthropic_model_sends_grounding_system_prompt(monkeypatch):
    import sys
    from types import ModuleType, SimpleNamespace

    from konigsberg_harness.models import AnthropicModel, UserMsg

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    calls: list = []

    class _Msgs:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text="ok")],
            )

    mod = ModuleType("anthropic")

    class Anthropic:
        def __init__(self, api_key: str):
            self.messages = _Msgs()

    mod.Anthropic = Anthropic
    monkeypatch.setitem(sys.modules, "anthropic", mod)

    m = AnthropicModel()
    m.respond([UserMsg("hi")], tools=[], tier=Tier.CHEAP)
    assert calls and calls[0]["system"] == GROUNDING_SYSTEM_PROMPT


def test_assistant_final_event_carries_zones():
    """Live event stream exposes commentary + failures for REPL rendering."""
    from konigsberg_harness.session import Session

    class _Args(BaseModel):
        x: int = 1

    reg = ToolRegistry()

    def boom(x: int = 1):
        raise RuntimeError("nope")

    reg.register("t", boom, "doc", args_model=_Args)

    class ScriptedModel:
        def respond(self, history, tools, *, tier):
            if not getattr(self, "_done", False):
                self._done = True
                return [ToolCall(id="1", name="t", args={})]
            return AssistantText("fabricated verdict")

    sess = Session.create()
    from konigsberg_harness.models import UserMsg

    sess.history.append(UserMsg("q"))
    events = list(Agent(reg, ScriptedModel()).step(sess))
    finals = [e for e in events if isinstance(e, AssistantFinal)]
    assert len(finals) == 1
    assert finals[0].failures == ("t",)
    assert "nothing established" in finals[0].text
    assert finals[0].commentary == "fabricated verdict"
