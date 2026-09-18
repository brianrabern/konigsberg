"""Working lemma notebook + hunt-until-proved loop."""
from __future__ import annotations

from konigsberg_harness.agent import (
    CAMPAIGN_DISPROVED,
    CAMPAIGN_PROVED,
    Agent,
    AgentConfig,
    campaign_settlement,
)
from konigsberg_harness.ledger import mint_certificate, mint_lean_proof
from konigsberg_harness.lemmas import LemmaNotebook, LockedLemma, lemma_list, lemma_read
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall
from konigsberg_harness.session import Session, SessionStore
from konigsberg_harness.tools.arg_models import (
    BkPredicateArgs,
    LeanCheckArgs,
    LeanProveArgs,
)
from konigsberg_harness.tools.registry import ToolRegistry


class ScriptedModel:
    def __init__(self, responses: list):
        self._responses = list(responses)
        self.histories: list[list[HistoryItem]] = []

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        self.histories.append(list(history))
        if not self._responses:
            return AssistantText("(exhausted)")
        return self._responses.pop(0)


def test_notebook_lock_replace_and_read():
    nb = LemmaNotebook()
    nb.lock(LockedLemma(lean_name="foo", snippet="theorem foo : True := trivial"))
    nb.lock(LockedLemma(lean_name="foo", snippet="theorem foo : True := by trivial"))
    assert len(nb.lemmas) == 1
    assert "by trivial" in lemma_read(nb, "foo")
    assert "foo" in lemma_list(nb)
    assert "no locked lemma" in lemma_read(nb, "missing")


def test_session_lemma_round_trip(tmp_path):
    store = SessionStore(tmp_path)
    sess = store.create()
    lemma = LockedLemma(
        lean_name="bar",
        snippet="theorem bar : True := trivial",
        durable=True,
        axioms=("propext",),
    )
    store.log_lemma(sess, lemma)
    loaded = store.load(sess.id)
    assert len(loaded.notebook.lemmas) == 1
    got = loaded.notebook.get("bar")
    assert got is not None
    assert got.durable is True
    assert got.snippet.startswith("theorem bar")


def test_chat_lean_prove_locks_snippet_without_stopping_early():
    reg = ToolRegistry()
    reg.register(
        "lean_prove",
        lambda lean_name, snippet, durable=False: mint_lean_proof(
            lean_name, axioms=("propext",), tool="lean_prove", durable=durable
        ),
        args_model=LeanProveArgs,
    )
    model = ScriptedModel(
        [
            [
                ToolCall(
                    id="1",
                    name="lean_prove",
                    args={
                        "lean_name": "foo",
                        "snippet": "theorem foo : True := trivial",
                    },
                )
            ],
            AssistantText("done"),
        ]
    )
    session = Session.create()
    result = Agent(reg, model).run("prove foo", session=session)
    assert result.commentary == "done"
    assert len(session.notebook.lemmas) == 1
    assert session.notebook.lemmas[0].lean_name == "foo"
    assert "True := trivial" in session.notebook.lemmas[0].snippet


def test_hunt_continues_past_prose_until_lean_prove():
    reg = ToolRegistry()
    reg.register(
        "lean_prove",
        lambda lean_name, snippet, durable=False: mint_lean_proof(
            lean_name, axioms=("propext",), tool="lean_prove"
        ),
        args_model=LeanProveArgs,
    )
    leftover = AssistantText("should not run")
    model = ScriptedModel(
        [
            AssistantText("I give up"),
            [
                ToolCall(
                    id="1",
                    name="lean_prove",
                    args={
                        "lean_name": "foo",
                        "snippet": "theorem foo : True := trivial",
                    },
                )
            ],
            leftover,
        ]
    )
    result = Agent(reg, model, AgentConfig(hunt=True, hunt_max_rounds=10)).run(
        "prove foo"
    )
    assert len(result.ledger.claims()) == 1
    assert result.ledger.claims()[0].statement == "foo"
    assert result.commentary and "Hunt stopped" in result.commentary
    assert result.session is not None
    assert result.session.notebook.get("foo") is not None
    assert model._responses == [leftover]


def test_hunt_emits_continued_on_prose():
    reg = ToolRegistry()
    model = ScriptedModel([AssistantText("not yet")])
    agent = Agent(reg, model, AgentConfig(hunt=True, hunt_max_rounds=1))
    session = Session.create()
    session.history.append(AssistantText("go"))
    events = [type(e).__name__ for e in agent.step(session)]
    assert "HuntContinued" in events
    assert "AssistantFinal" not in events


def test_hunt_round_cap_without_proof():
    reg = ToolRegistry()
    model = ScriptedModel([AssistantText("nope"), AssistantText("still no")])
    result = Agent(reg, model, AgentConfig(hunt=True, hunt_max_rounds=2)).run("prove")
    assert result.final is None
    assert result.ledger.claims() == ()
    assert result.steps == 2


_BK_SNIPPET = """
theorem BorodinKostochka {V} (G : SimpleGraph V)
    (hΔ : G.maxDegree ≥ 9) :
    G.chromaticNumber ≤ max (G.maxDegree - 1) G.cliqueNum := by
  sorry
"""


class _State:
    """Stand-in for a LeanREPL GoalState with a fixed ``ok``."""

    def __init__(self, ok: bool) -> None:
        self.ok = ok
        self.errors: tuple = ()


def _prove_registry(bk_type_ok: bool = True) -> ToolRegistry:
    """``bk_type_ok`` models the kernel BK type-equality check: True ⇒ the proved
    theorem has the corpus BK type; False ⇒ it does not (e.g. `True := trivial`)."""

    def prove(lean_name, snippet, durable=False):
        return mint_lean_proof(
            lean_name, axioms=("propext",), tool="lean_prove", durable=durable
        )

    def lean_check(snippet):
        return _State(bk_type_ok)

    reg = ToolRegistry()
    reg.register("lean_prove", prove, args_model=LeanProveArgs)
    reg.register("lean_check", lean_check, args_model=LeanCheckArgs)
    return reg


def _bk_campaign_registry(bk_type_ok: bool = True) -> ToolRegistry:
    def predicate(graph6: str):
        if graph6 == "violates":
            return mint_certificate(
                "violates VIOLATES BK (Δ=9, ω=8, χ=9).",
                checker="list_checks.verify_chromatic_bundle",
                tool="bk_predicate",
            )
        return mint_certificate(
            f"{graph6} satisfies BK (Δ=9, ω=9, χ=9).",
            checker="list_checks.verify_chromatic_bundle",
            tool="bk_predicate",
        )

    reg = _prove_registry(bk_type_ok=bk_type_ok)
    reg.register("bk_predicate", predicate, args_model=BkPredicateArgs)
    return reg


def test_forever_does_not_stop_on_lean_prove():
    from konigsberg_harness.agent import FOREVER_CONTINUE

    leftover = AssistantText("third")
    model = ScriptedModel(
        [
            [
                ToolCall(
                    id="1",
                    name="lean_prove",
                    args={
                        "lean_name": "foo",
                        "snippet": "theorem foo : True := trivial",
                    },
                )
            ],
            AssistantText("lemma done, stopping"),
            leftover,
        ]
    )
    result = Agent(
        _prove_registry(),
        model,
        AgentConfig(hunt=True, hunt_forever=True, hunt_max_rounds=3),
    ).run("campaign")
    assert len(result.ledger.claims()) == 1
    assert result.final is None
    assert result.steps == 3
    assert result.session is not None
    assert result.session.notebook.get("foo") is not None
    assert leftover not in model._responses
    texts = [getattr(i, "text", "") for i in result.session.history]
    assert any(FOREVER_CONTINUE in t for t in texts)


def test_campaign_settlement_helpers():
    violate = mint_certificate(
        "IXxxx VIOLATES BK (Δ=9, ω=8, χ=9).",
        checker="list_checks.verify_chromatic_bundle",
        tool="bk_predicate",
    )
    assert campaign_settlement(violate) == "disproved"
    satisfies = mint_certificate(
        "IXxxx satisfies BK (Δ=9, ω=9, χ=9).",
        checker="list_checks.verify_chromatic_bundle",
        tool="bk_predicate",
    )
    assert campaign_settlement(satisfies) is None

    trivial = mint_lean_proof(
        "BorodinKostochka", axioms=("propext",), tool="lean_prove", durable=True
    )
    assert (
        campaign_settlement(
            trivial,
            ToolCall(
                id="1",
                name="lean_prove",
                args={
                    "lean_name": "BorodinKostochka",
                    "snippet": "theorem BorodinKostochka : True := trivial",
                    "durable": True,
                },
            ),
        )
        is None
    )

    session_only = mint_lean_proof(
        "BorodinKostochka", axioms=("propext",), tool="lean_prove", durable=False
    )
    assert (
        campaign_settlement(
            session_only,
            ToolCall(
                id="1",
                name="lean_prove",
                args={
                    "lean_name": "BorodinKostochka",
                    "snippet": _BK_SNIPPET,
                    "durable": False,
                },
            ),
        )
        is None
    )

    proved = mint_lean_proof(
        "BorodinKostochka", axioms=("propext",), tool="lean_prove", durable=True
    )
    assert (
        campaign_settlement(
            proved,
            ToolCall(
                id="1",
                name="lean_prove",
                args={
                    "lean_name": "BorodinKostochka",
                    "snippet": _BK_SNIPPET,
                    "durable": True,
                },
            ),
        )
        == "proved"
    )

    corpus = mint_lean_proof(
        "Konigsberg.Literature.Coloring.BorodinKostochka.borodinKostochka",
        axioms=("propext",),
        tool="lean_prove",
        durable=True,
    )
    assert (
        campaign_settlement(
            corpus,
            ToolCall(
                id="2",
                name="lean_prove",
                args={
                    "lean_name": (
                        "Konigsberg.Literature.Coloring.BorodinKostochka."
                        "borodinKostochka"
                    ),
                    "snippet": (
                        "theorem borodinKostochka (hΔ : 9 ≤ G.maxDegree) :\n"
                        "    G.Colorable (max (G.maxDegree - 1) G.cliqueNum) := by\n"
                        "  omega"
                    ),
                    "durable": True,
                },
            ),
        )
        == "proved"
    )

    bridge = mint_lean_proof(
        "BK.reducible_of_fChoosable",
        axioms=("propext",),
        tool="lean_prove",
        durable=True,
    )
    assert (
        campaign_settlement(
            bridge,
            ToolCall(
                id="1",
                name="lean_prove",
                args={
                    "lean_name": "BK.reducible_of_fChoosable",
                    "snippet": _BK_SNIPPET,
                    "durable": True,
                },
            ),
        )
        is None
    )


def test_campaign_settlement_kernel_gate():
    """Live halt requires the kernel type-check, not the snippet heuristic.

    A durable, BK-named, keyword-matching proof must NOT settle unless a kernel
    check confirms its type equals the corpus BK statement — this closes the
    false-PROVED hole where a flailing model proves a durable triviality named
    BorodinKostochka.
    """
    call = ToolCall(
        id="1",
        name="lean_prove",
        args={"lean_name": "BorodinKostochka", "snippet": _BK_SNIPPET, "durable": True},
    )
    proved = mint_lean_proof(
        "BorodinKostochka", axioms=("propext",), tool="lean_prove", durable=True
    )
    # Verifier rejects the type ⇒ no settlement, despite name + snippet looking BK.
    assert campaign_settlement(proved, call, verify_type=lambda _n: False) is None
    # Verifier confirms the corpus type ⇒ settlement.
    assert campaign_settlement(proved, call, verify_type=lambda _n: True) == "proved"

    # Axiom-dirty (e.g. routed through the corpus `sorry` decl) never settles,
    # even if the verifier would pass.
    dirty = mint_lean_proof(
        "BorodinKostochka",
        axioms=("propext", "sorryAx"),
        tool="lean_prove",
        durable=True,
    )
    assert campaign_settlement(dirty, call, verify_type=lambda _n: True) is None


def test_forever_stops_on_bk_proof():
    leftover = AssistantText("should not run")
    model = ScriptedModel(
        [
            [
                ToolCall(
                    id="1",
                    name="lean_prove",
                    args={
                        "lean_name": "BorodinKostochka",
                        "snippet": _BK_SNIPPET,
                        "durable": True,
                    },
                )
            ],
            leftover,
        ]
    )
    result = Agent(
        _prove_registry(),
        model,
        AgentConfig(hunt=True, hunt_forever=True, hunt_max_rounds=5),
    ).run("campaign")
    assert result.steps == 1
    assert leftover in model._responses
    assert result.commentary == CAMPAIGN_PROVED
    assert result.final is not None
    assert CAMPAIGN_PROVED in result.final


def test_forever_stops_on_bk_violation():
    leftover = AssistantText("should not run")
    model = ScriptedModel(
        [
            [
                ToolCall(
                    id="1",
                    name="bk_predicate",
                    args={"graph6": "violates"},
                )
            ],
            leftover,
        ]
    )
    result = Agent(
        _bk_campaign_registry(),
        model,
        AgentConfig(hunt=True, hunt_forever=True, hunt_max_rounds=5),
    ).run("campaign")
    assert result.steps == 1
    assert leftover in model._responses
    assert result.commentary == CAMPAIGN_DISPROVED
    assert result.final is not None


def test_forever_does_not_stop_on_satisfies_or_trivial_name():
    leftover = AssistantText("third")
    model = ScriptedModel(
        [
            [
                ToolCall(
                    id="1",
                    name="bk_predicate",
                    args={"graph6": "ok"},
                )
            ],
            [
                ToolCall(
                    id="2",
                    name="lean_prove",
                    args={
                        "lean_name": "BorodinKostochka",
                        "snippet": "theorem BorodinKostochka : True := trivial",
                        "durable": True,
                    },
                )
            ],
            leftover,
        ]
    )
    result = Agent(
        # Kernel rejects the type: `True := trivial` is not the BK statement.
        _bk_campaign_registry(bk_type_ok=False),
        model,
        AgentConfig(hunt=True, hunt_forever=True, hunt_max_rounds=2),
    ).run("campaign")
    assert result.final is None
    assert result.steps == 2
    assert leftover in model._responses
    assert len(result.ledger.claims()) == 2
