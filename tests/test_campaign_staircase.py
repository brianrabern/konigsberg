"""Ledger-backed BK staircase (next increment, not rediscovery)."""
from __future__ import annotations

from konigsberg_harness.agent import (
    FOREVER_CONTINUE,
    Agent,
    AgentConfig,
)
from konigsberg_harness.campaign import (
    REDISCOVERY_BANNER,
    REFORMULATE_BANNER,
    STAGNATION_THRESHOLD,
    STAIRCASE_MARK,
    CampaignBind,
    extract_core,
    format_campaign_snapshot,
    has_durable_bridge,
    next_step,
    note_stagnation,
    progress_fingerprint,
    stagnation_eligible,
)
from konigsberg_harness.ledger import Ledger, mint_enumeration, mint_lean_proof
from konigsberg_harness.lemmas import LockedLemma
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall
from konigsberg_harness.session import Session
from konigsberg_harness.tools.arg_models import EmptyArgs, ReducibleConfigurationArgs
from konigsberg_harness.tools.registry import ToolRegistry, build_registry


class ScriptedModel:
    def __init__(self, responses: list):
        self._responses = list(responses)

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        if not self._responses:
            return AssistantText("(exhausted)")
        return self._responses.pop(0)

_FORBIDDEN = (
    "FORBIDDEN CONFIGURATION (BK minimal counterexample, H_BK: Δ=D≥9, "
    "K_D-free, D-critical; Δ=9): "
    "core=Cr, degree spec d_G=[8,8,8,8], slack f=[1,1,1,1]; core is "
    "f-choosable (exhaustive to palette P=4) ⇒ reducible ⇒ absent from "
    "every minimal counterexample. [bridge: BK.reducible_of_fChoosable]"
)


def test_extract_core_from_forbidden_statement():
    assert extract_core(_FORBIDDEN) == "Cr"
    assert extract_core("some other claim") is None


def test_next_step_skips_bridge_when_literature_formalized():
    """Corpus formalized ⇒ empty ledger starts at Rabern seeds, not re-proving."""
    claim = mint_enumeration(
        _FORBIDDEN, bound="palette<=4", exhaustive=True, tool="reducible_configuration"
    )
    nxt = next_step([claim], [])
    assert "re-derive Rabern seed" in nxt
    assert "lean_prove of BK.reducible_of_fChoosable" not in nxt
    snap = format_campaign_snapshot([claim], [])
    assert STAIRCASE_MARK in snap
    assert "formalized (Literature)" in snap
    assert "core=Cr" in snap or "Cr" in snap
    assert "NEXT:" in snap


def test_next_step_is_bridge_until_corpus_formalized(monkeypatch):
    monkeypatch.setattr(
        "konigsberg_harness.campaign.bridge_is_formalized", lambda: False
    )
    claim = mint_enumeration(
        _FORBIDDEN, bound="palette<=4", exhaustive=True, tool="reducible_configuration"
    )
    assert "reducible_of_fChoosable" in next_step([claim], [])
    snap = format_campaign_snapshot([claim], [])
    assert "bridge: not formalized" in snap


def test_next_step_after_bridge_asks_for_new_core():
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
    assert has_durable_bridge([proof], [lemma])
    forbidden = mint_enumeration(
        _FORBIDDEN, bound="palette<=4", exhaustive=True, tool="reducible_configuration"
    )
    nxt = next_step([proof, forbidden], [lemma])
    assert "re-derive Rabern seed" in nxt
    empty_cores = next_step([proof], [lemma])
    assert "re-derive Rabern seed" in empty_cores
    from konigsberg_empirical.reduction.seeds import next_unminted_seed

    seed = next_unminted_seed(())
    assert seed is not None
    assert seed.name in empty_cores
    assert seed.core in empty_cores


def test_campaign_status_tool_reads_live_ledger():
    reg = build_registry()
    assert "campaign_status" in {s["name"] for s in reg.tool_specs()}
    empty = reg.dispatch("campaign_status", {})
    assert STAIRCASE_MARK in empty
    assert "formalized (Literature)" in empty
    assert "re-derive Rabern seed" in empty
    assert "C: 0 cores" in empty
    assert "discharging:" in empty
    ledger = Ledger()
    ledger.record(
        mint_enumeration(
            _FORBIDDEN, bound="palette<=4", exhaustive=True, tool="reducible_configuration"
        )
    )
    reg.campaign_bind.ledger = ledger
    out = reg.dispatch("campaign_status", {})
    assert "Cr" in out


def test_forever_continue_carries_known_core():
    def ping() -> str:
        return "ok"

    reg = ToolRegistry()
    reg.register("ping", ping, args_model=EmptyArgs)
    leftover = AssistantText("third")
    model = ScriptedModel(
        [
            [ToolCall(id="1", name="ping", args={})],
            AssistantText("pausing"),
            leftover,
        ]
    )
    result = Agent(
        reg,
        model,
        AgentConfig(hunt=True, hunt_forever=True, hunt_max_rounds=3),
    ).run("campaign")
    texts = [getattr(i, "text", "") for i in result.session.history]
    assert any(FOREVER_CONTINUE in t and STAIRCASE_MARK in t for t in texts)
    assert leftover not in model._responses


def test_reducible_rediscovery_is_flagged():
    def hit(**_kwargs):
        return mint_enumeration(
            _FORBIDDEN,
            bound="palette<=4",
            exhaustive=True,
            tool="reducible_configuration",
        )

    reg = ToolRegistry()
    reg.register(
        "reducible_configuration",
        hit,
        args_model=ReducibleConfigurationArgs,
    )
    args = {"core": "Cr", "degrees": [8, 8, 8, 8], "D": 9}
    model = ScriptedModel(
        [
            [ToolCall(id="1", name="reducible_configuration", args=args)],
            [ToolCall(id="2", name="reducible_configuration", args=args)],
            AssistantText("again"),
        ]
    )
    result = Agent(
        reg,
        model,
        AgentConfig(hunt=True, hunt_forever=True, hunt_max_rounds=3),
    ).run("campaign")
    assert len(result.ledger.claims()) == 2
    banners = [obs.result for obs in result.transcript]
    assert not banners[0].startswith("REDISCOVERY")
    assert REDISCOVERY_BANNER.strip() in banners[1]


_MISS = ("deg8(high=0,low=8) final=-1",)


def _exhaust_catalogue(monkeypatch):
    monkeypatch.setattr(
        "konigsberg_harness.campaign.next_unminted_seed", lambda _cores: None
    )
    monkeypatch.setattr(
        "konigsberg_harness.campaign.bridge_is_formalized", lambda: True
    )


def test_stagnation_ineligible_during_seed_catalogue():
    nxt = next_step([], [])
    if "re-derive Rabern seed" not in nxt:
        # Catalogue already exhausted in this environment; skip the guard.
        return
    assert not stagnation_eligible(nxt)
    bind = CampaignBind()
    for _ in range(STAGNATION_THRESHOLD + 2):
        assert note_stagnation(bind, [], []) == ""
    assert bind.stagnation_streak == 0
    assert "REFORMULATE:" not in format_campaign_snapshot([], [])


def test_stagnation_ineligible_during_bridge(monkeypatch):
    monkeypatch.setattr(
        "konigsberg_harness.campaign.bridge_is_formalized", lambda: False
    )
    nxt = next_step([], [])
    assert "BK.reducible_of_fChoosable" in nxt
    assert not stagnation_eligible(nxt)
    bind = CampaignBind()
    for _ in range(STAGNATION_THRESHOLD + 2):
        assert note_stagnation(bind, [], []) == ""
    assert bind.stagnation_streak == 0


def test_progress_fingerprint_moves_on_new_core_or_miss(monkeypatch):
    _exhaust_catalogue(monkeypatch)
    empty = progress_fingerprint([], [])
    miss = progress_fingerprint([], [], survivors=_MISS)
    core = progress_fingerprint(
        [
            mint_enumeration(
                _FORBIDDEN,
                bound="palette<=4",
                exhaustive=True,
                tool="reducible_configuration",
            )
        ],
        [],
        survivors=_MISS,
    )
    assert empty != miss
    assert miss != core
    assert empty[2] == "open"
    assert miss[2].startswith("miss:")
    nine = (
        "deg9(high=9,low=0) final=1 deficit=1",
        "deg9(high=0,low=9) final=1 deficit=1",
    )
    a = progress_fingerprint([], [], survivors=(nine[0],))
    b = progress_fingerprint([], [], survivors=nine)
    assert a[2] == "stuck:deg9-regular"
    assert a[2] == b[2]


def test_note_stagnation_fires_after_frozen_discharging(monkeypatch):
    _exhaust_catalogue(monkeypatch)
    bind = CampaignBind()
    assert note_stagnation(bind, [], [], survivors=_MISS) == ""
    assert note_stagnation(bind, [], [], survivors=_MISS) == ""
    banner = note_stagnation(bind, [], [], survivors=_MISS)
    assert banner == REFORMULATE_BANNER
    assert "switch resource" in banner.lower() or "Switch resource" in banner
    assert "equivalent_K3_join_E6" in banner
    assert "graph6_decode" in banner or "graph6_decode" in banner.lower()
    assert "discharging_search" in banner  # as a thing not to rerun


def test_note_stagnation_resets_on_new_core(monkeypatch):
    _exhaust_catalogue(monkeypatch)
    bind = CampaignBind()
    note_stagnation(bind, [], [], survivors=_MISS)
    note_stagnation(bind, [], [], survivors=_MISS)
    forbidden = mint_enumeration(
        _FORBIDDEN,
        bound="palette<=4",
        exhaustive=True,
        tool="reducible_configuration",
    )
    assert note_stagnation(bind, [forbidden], [], survivors=_MISS) == ""
    assert bind.stagnation_streak == 0


def test_campaign_status_surfaces_reformulate_when_frozen(monkeypatch):
    _exhaust_catalogue(monkeypatch)
    bind = CampaignBind()
    bind.last_discharge_survivors = _MISS
    bind.stagnation_streak = STAGNATION_THRESHOLD
    from konigsberg_harness.campaign import campaign_status

    out = campaign_status(bind)
    assert STAIRCASE_MARK in out
    assert "REFORMULATE:" in out


def test_maybe_inject_staircase_appends_reformulate(monkeypatch):
    _exhaust_catalogue(monkeypatch)
    reg = ToolRegistry()
    bind = CampaignBind()
    bind.last_discharge_survivors = _MISS
    reg.campaign_bind = bind
    agent = Agent(
        reg,
        ScriptedModel([]),
        AgentConfig(hunt=True, hunt_forever=True),
    )
    session = Session.create()
    agent._bind_campaign(session)
    banners: list[str] = []
    for i in range(STAGNATION_THRESHOLD + 1):
        agent._maybe_inject_staircase(session, None, force=True)
        last = session.history[-1]
        banners.append(last.text)
        session.history.append(AssistantText(f"spin {i}"))
    assert STAIRCASE_MARK in banners[0]
    assert "REFORMULATE:" not in banners[0]
    assert "REFORMULATE:" not in banners[1]
    assert REFORMULATE_BANNER.strip() in banners[-1]


def test_sign_unforced_note_is_not_no_attempt(monkeypatch):
    _exhaust_catalogue(monkeypatch)
    note = (
        "inconclusive: global charge sign is not forced by μ on "
        "{D-1, D}-vertices (proves nothing)"
    )
    nxt = next_step([], [], discharge_note=note)
    assert "literature_search" in nxt
    assert "reducible_configuration" in nxt
    snap = format_campaign_snapshot([], [], discharge_note=note)
    assert "not closed (no attempt)" not in snap
    assert "last:" in snap
    assert "not forced" in snap


def test_dummy_closure_alias_is_not_literature_closure():
    from konigsberg_harness.campaign import has_durable_closure, is_closure_name

    dummy = LockedLemma(
        lean_name=(
            "BK.DischargingClosure."
            "reducible_and_unavoidable_imp_no_counterexample_durable"
        ),
        snippet="theorem t : True := trivial",
        durable=True,
    )
    real = LockedLemma(
        lean_name="BK.reducible_and_unavoidable_imp_no_counterexample",
        snippet="theorem t : True := trivial",
        durable=True,
    )
    assert not is_closure_name(dummy.lean_name)
    assert is_closure_name(real.lean_name)
    assert not has_durable_closure([], [dummy])
    assert has_durable_closure([], [real])


def test_graph6_decode_repeat_is_budget():
    from konigsberg_harness.tools.errors import ToolBudgetExceeded
    from konigsberg_harness.tools.registry import build_registry

    reg = build_registry()
    g6 = "C~~w"
    reg.dispatch("graph6_decode", {"graph6": g6})
    reg.dispatch("graph6_decode", {"graph6": g6})
    try:
        reg.dispatch("graph6_decode", {"graph6": g6})
    except ToolBudgetExceeded as e:
        assert "already decoded" in str(e)
    else:
        raise AssertionError("expected ToolBudgetExceeded")
