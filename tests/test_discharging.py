"""Discharging engine (D=9) + settlement boundary vs general BK."""

from __future__ import annotations

import pytest
from konigsberg_empirical.discharging import (
    CLOSURE_TAG,
    DischargeRejected,
    build_argument,
    local_types,
    verify_unavoidable,
)
from konigsberg_empirical.fundamentals.codec import graph6_encode
from konigsberg_empirical.reduction.seeds import load_reducible_seeds
from konigsberg_harness.agent import Agent, AgentConfig, campaign_settlement, settles_bk_at
from konigsberg_harness.campaign import has_unavoidable, next_step
from konigsberg_harness.ledger import Claim, Ledger, mint_enumeration, mint_lean_proof
from konigsberg_harness.lemmas import LockedLemma
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall
from konigsberg_harness.tools.arg_models import DischargingArgs, LeanProveArgs
from konigsberg_harness.tools.empirical_tools import DischargingResult
from konigsberg_harness.tools.registry import ToolRegistry, build_registry


class ScriptedModel:
    def __init__(self, responses: list):
        self._responses = list(responses)

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        if not self._responses:
            return AssistantText("(exhausted)")
        return self._responses.pop(0)


def _edge() -> str:
    return graph6_encode(2, [(0, 1)])


def _triangle() -> str:
    return graph6_encode(3, [(0, 1), (0, 2), (1, 2)])


def _forbidden(core: str) -> Claim:
    return mint_enumeration(
        f"FORBIDDEN CONFIGURATION (BK): core={core}, degree spec d_G=[8,8]",
        bound="palette<=4",
        exhaustive=True,
        tool="reducible_configuration",
    )


def _bridge() -> tuple[Claim, LockedLemma]:
    proof = mint_lean_proof(
        "BK.reducible_of_fChoosable",
        axioms=("propext",),
        tool="lean_prove",
        durable=True,
    )
    lemma = LockedLemma(
        lean_name="BK.reducible_of_fChoosable",
        snippet="theorem reducible_of_fChoosable : True := trivial",
        durable=True,
    )
    return proof, lemma


def test_local_types_d9_are_degree_signatures():
    types = local_types(9)
    assert len(types) == 19
    assert {t.center_deg for t in types} == {8, 9}


def test_global_sign_zero_plus_high_is_forced():
    from konigsberg_empirical.discharging import global_sign, intended_sign

    assert global_sign({8: 0, 9: 1}, 9) == 1
    assert global_sign({8: 0, 9: -1}, 9) == -1
    assert global_sign({8: -1, 9: 1}, 9) is None
    assert intended_sign({8: -1, 9: 1}, 9) == 1


def test_mixed_mu_ranks_residuals_but_cannot_hit():
    arg = build_argument(9, {8: -1, 9: 1}, [], [])
    result = verify_unavoidable(arg, reducible_cores=set())
    assert not result.hit
    assert result.global_sign is None
    assert result.ranked
    assert result.ranked[0].deficit <= result.ranked[-1].deficit
    assert "cannot HIT" in result.reason


def test_engine_miss_ranked_includes_deficit():
    core = _triangle()
    arg = build_argument(9, {8: -1, 9: -1}, [], [core])
    result = verify_unavoidable(arg, reducible_cores={core})
    assert not result.hit
    assert result.ranked
    assert "deficit=" in result.survivors[0]
    assert result.checked == 19


def test_engine_close_on_forced_edge():
    core = _edge()
    arg = build_argument(9, {8: -1, 9: -1}, [], [core])
    result = verify_unavoidable(arg, reducible_cores={core})
    assert result.hit
    assert result.survivors == ()
    assert "UNAVOIDABLE" in result.reason
    assert CLOSURE_TAG in result.reason
    assert "avoidable" not in result.reason.lower().replace("unavoidable", "")


def test_engine_miss_returns_survivors():
    core = _triangle()
    arg = build_argument(9, {8: -1, 9: -1}, [], [core])
    result = verify_unavoidable(arg, reducible_cores={core})
    assert not result.hit
    assert result.survivors
    assert "inconclusive" in result.reason
    assert "avoidable" not in result.reason.lower()


def test_engine_non_conserving_rejects():
    core = _edge()
    arg = build_argument(
        9, {8: -1, 9: -1}, [{"from_deg": 9, "to_pattern": "self", "amount": 1}], [core]
    )
    with pytest.raises(DischargeRejected, match="non-conserving"):
        verify_unavoidable(arg, reducible_cores={core})


def test_engine_ledger_coupling():
    core = _edge()
    arg = build_argument(9, {8: -1, 9: -1}, [], [core])
    with pytest.raises(DischargeRejected, match="ledger coupling"):
        verify_unavoidable(arg, reducible_cores=set())


def test_tool_hit_and_miss_via_registry():
    core = _edge()
    reg = build_registry()
    ledger = Ledger()
    ledger.record(_forbidden(core))
    reg.campaign_bind.ledger = ledger
    hit = reg.dispatch(
        "discharging_unavoidable",
        {"D": 9, "mu": {8: -1, 9: -1}, "rules": [], "forbidden": [core]},
    )
    assert isinstance(hit, Claim)
    assert "UNAVOIDABLE" in hit.statement
    assert CLOSURE_TAG in hit.statement
    assert has_unavoidable([_forbidden(core), hit])
    assert not has_unavoidable([hit])  # coupling: UNAVOIDABLE without reducible 𝒞

    tri = _triangle()
    ledger.record(_forbidden(tri))
    miss = reg.dispatch(
        "discharging_unavoidable",
        {"D": 9, "mu": {8: -1, 9: -1}, "rules": [], "forbidden": [tri]},
    )
    assert isinstance(miss, DischargingResult)
    assert miss.survivors
    assert "avoidable" not in str(miss).lower()
    assert reg.campaign_bind.last_discharge_survivors == miss.survivors
    assert "surviving" in reg.campaign_bind.last_discharge_note
    status = reg.dispatch("campaign_status", {})
    assert "last miss:" in status
    assert "C:" in status


def test_next_step_opens_full_instrument_after_seeds():
    proof, lemma = _bridge()
    cores = [_forbidden(seed.core) for seed in load_reducible_seeds()]
    nxt = next_step([proof, *cores], [lemma])
    assert "reducible_configuration" in nxt
    assert "literature_search" in nxt
    assert "lean_prove" in nxt
    assert "deg9(high=9,low=0)" in nxt


def test_settles_bk_at_nine_is_not_general_settlement():
    at_nine = mint_lean_proof(
        "borodinKostochka_at_nine",
        axioms=("propext",),
        tool="lean_prove",
        durable=True,
    )
    call = ToolCall(
        id="1",
        name="lean_prove",
        args={
            "lean_name": "borodinKostochka_at_nine",
            "snippet": (
                "theorem borodinKostochka_at_nine (hΔ : G.maxDegree = 9) : "
                "G.Colorable (max 8 G.cliqueNum) := by sorry"
            ),
            "durable": True,
        },
    )
    assert settles_bk_at(at_nine, call) == 9
    assert campaign_settlement(at_nine, call) is None
    assert (
        campaign_settlement(at_nine, call, verify_type=lambda _n: True) is None
    )


def test_forever_does_not_halt_on_at_nine():
    def prove(**_kwargs):
        return mint_lean_proof(
            "borodinKostochka_at_nine",
            axioms=("propext",),
            tool="lean_prove",
            durable=True,
        )

    reg = ToolRegistry()
    reg.register("lean_prove", prove, args_model=LeanProveArgs)
    leftover = AssistantText("should still run")
    model = ScriptedModel(
        [
            [
                ToolCall(
                    id="1",
                    name="lean_prove",
                    args={
                        "lean_name": "borodinKostochka_at_nine",
                        "snippet": (
                            "theorem borodinKostochka_at_nine "
                            "(hΔ : G.maxDegree = 9) : "
                            "G.Colorable (max 8 G.cliqueNum) := trivial"
                        ),
                        "durable": True,
                    },
                )
            ],
            leftover,
        ]
    )
    result = Agent(
        reg,
        model,
        AgentConfig(hunt=True, hunt_forever=True, hunt_max_rounds=2),
    ).run("campaign")
    assert leftover not in model._responses
    assert result.final is None
    assert campaign_settlement(result.ledger.claims()[0], None) is None


def test_discharging_args_schema():
    spec = {s["name"]: s for s in build_registry().tool_specs()}
    assert spec["discharging_unavoidable"]["input_schema"]["properties"].keys() >= {
        "D",
        "mu",
        "rules",
        "forbidden",
    }
    assert spec["discharging_search"]["input_schema"]["properties"].keys() >= {
        "D",
        "mu",
        "rules",
        "max_iters",
    }
    DischargingArgs.model_validate(
        {"D": 9, "mu": {8: -1, 9: -1}, "rules": [], "forbidden": ["A_"]}
    )


def test_untagged_unavoidable_does_not_close_staircase():
    proof, lemma = _bridge()
    seeds = [_forbidden(seed.core) for seed in load_reducible_seeds()]
    fake = mint_enumeration(
        "UNAVOIDABLE (BK D=9 discharging): cores=Bg in every 9-critical graph.",
        bound="D=9",
        exhaustive=True,
        tool="discharging_unavoidable",
    )
    assert not has_unavoidable([proof, *seeds, fake])
    nxt = next_step([proof, *seeds, fake], [lemma])
    assert "Stand on Rabern" in nxt
    assert (
        "durable lean_prove of "
        "BK.reducible_and_unavoidable_imp_no_counterexample" not in nxt
    )


def test_unavoidable_cores_must_be_on_reducible_ledger():
    proof, _lemma = _bridge()
    seeds = [_forbidden(seed.core) for seed in load_reducible_seeds()]
    fake = mint_enumeration(
        f"UNAVOIDABLE (BK D=9 discharging): cores=ZZZZ in every 9-critical. {CLOSURE_TAG}",
        bound="D=9",
        exhaustive=True,
        tool="discharging_unavoidable",
    )
    assert not has_unavoidable([proof, *seeds, fake])


def test_tagged_unavoidable_over_ledger_cores_asks_for_closure():
    proof, lemma = _bridge()
    seeds = [_forbidden(seed.core) for seed in load_reducible_seeds()]
    first = load_reducible_seeds()[0].core
    hit = mint_enumeration(
        f"UNAVOIDABLE (BK D=9 discharging): cores={first} in every 9-critical. "
        f"{CLOSURE_TAG}",
        bound="D=9",
        exhaustive=True,
        tool="discharging_unavoidable",
    )
    assert has_unavoidable([proof, *seeds, hit])
    nxt = next_step([proof, *seeds, hit], [lemma])
    assert "reducible_and_unavoidable" in nxt


def test_snapshot_is_two_dimensional():
    from konigsberg_harness.campaign import format_campaign_snapshot

    snap = format_campaign_snapshot(
        [], [], survivors=("deg8(high=0,low=8) final=-1",)
    )
    assert "C: 0 cores" in snap
    assert "last miss:" in snap
    assert "deg8(high=0,low=8)" in snap
    nxt = next_step([], [], survivors=("deg8(high=0,low=8) final=-1",))
    assert "re-derive Rabern seed" in nxt
    assert "lean_prove of BK.reducible_of_fChoosable" not in nxt


def test_miss_survivors_redirect_to_targeted_core():
    proof, lemma = _bridge()
    seeds = [_forbidden(seed.core) for seed in load_reducible_seeds()]
    nxt = next_step(
        [proof, *seeds],
        [lemma],
        survivors=("deg8(high=0,low=8) final=-1",),
    )
    assert "surviving neighborhood" in nxt
    assert "reducible_configuration" in nxt
    assert "do not rerun" in nxt.lower()
    assert "literature_search" in nxt


def test_sufficient_only_guard_rejects_banned_verdicts():
    from konigsberg_empirical.sufficient_only import assert_sufficient_only

    assert_sufficient_only("UNAVOIDABLE in D-critical graphs")
    assert_sufficient_only("inconclusive: method proves nothing")
    with pytest.raises(RuntimeError, match="sufficient-only"):
        assert_sufficient_only("this configuration is not reducible")
    with pytest.raises(RuntimeError, match="sufficient-only"):
        assert_sufficient_only("the set is avoidable")


def test_mission_bk_carries_discharging_rungs():
    from konigsberg_harness.grounding import MISSION_BK

    assert "discharging_unavoidable" in MISSION_BK
    assert "discharging_search" in MISSION_BK
    assert "borodinKostochka_at_nine" in MISSION_BK
    assert "TWO-DIMENSIONAL" in MISSION_BK
    assert "v1: D=9" in MISSION_BK
    assert "not reducible" not in MISSION_BK
    low = MISSION_BK.lower().replace("unavoidable", "")
    assert "avoidable" not in low
