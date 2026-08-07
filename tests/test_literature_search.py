"""Literature corpus index + literature_search (no Claim minting)."""
from __future__ import annotations

from pathlib import Path

import pytest
from konigsberg_harness.agent import Agent, AssistantFinal
from konigsberg_harness.context.library_map import library_map, literature_search
from konigsberg_harness.grounding import format_grounded_answer, format_references_zone
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall
from konigsberg_harness.session import Session
from konigsberg_harness.tools.registry import build_registry

LIT = Path("formal/Konigsberg/Literature")


def test_library_map_parses_status_and_external():
    catalog = library_map(LIT)
    names = {e.name for e in catalog}
    assert "RabernBook_FirstListBound" in names
    assert "RabernBook_SecondListBound" in names
    assert "Rabern_4ListCriticalEdgeBound" in names
    assert "CranstonRabern_ImprovedEdgeBound" in names
    assert "KiersteadRabern_OreVizing" in names
    assert "BrooksLean" in names
    # on-disk status.toml count + one EXTERNAL entry
    n_status = len(list(LIT.glob("**/status.toml")))
    assert len([e for e in catalog if e.source == "in-tree"]) == n_status
    assert len([e for e in catalog if e.source == "external"]) == 1


def test_library_map_malformed_toml_fails_loudly(tmp_path):
    bad = tmp_path / "Broken" / "status.toml"
    bad.parent.mkdir()
    bad.write_text("[entry]\nname = \"x\"\n<<<\n", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed TOML"):
        library_map(tmp_path)


def test_literature_search_rabern_statuses():
    hits = literature_search("Rabern", root=LIT)
    by_name = {}
    for h in hits:
        by_name.setdefault(h["name"], set()).add(h["status"])

    assert "RabernBook_FirstListBound" in by_name
    assert by_name["RabernBook_FirstListBound"] == {"formalized"}
    assert "RabernBook_SecondListBound" in by_name
    assert by_name["RabernBook_SecondListBound"] == {"formalized"}
    assert "Rabern_4ListCriticalEdgeBound" in by_name
    assert by_name["Rabern_4ListCriticalEdgeBound"] == {"stated"}
    assert "CranstonRabern_ImprovedEdgeBound" in by_name
    assert by_name["CranstonRabern_ImprovedEdgeBound"] == {"stated"}
    assert "KiersteadRabern_OreVizing" in by_name
    assert by_name["KiersteadRabern_OreVizing"] == {"stated"}
    assert "BrooksLean" in by_name
    assert by_name["BrooksLean"] == {"external-verified"}


def test_literature_search_status_filter_formalized():
    hits = literature_search("Rabern", status="formalized", root=LIT)
    assert hits
    assert all(h["status"] == "formalized" for h in hits)
    names = {h["name"] for h in hits}
    assert "RabernBook_FirstListBound" in names
    assert "Rabern_4ListCriticalEdgeBound" not in names


def test_stated_status_carried_verbatim_never_upgraded():
    hits = literature_search("4ListCritical", root=LIT)
    stated = [h for h in hits if h["status"] == "stated"]
    assert stated
    for h in stated:
        assert h["status"] == "stated"  # verbatim
        assert "formalized" not in h["status"]
        assert "proven" not in h["status"]


def test_literature_search_registered_lean_free_no_claims():
    reg = build_registry()
    assert "literature_search" in reg.names()
    hits = reg.dispatch("literature_search", {"query": "BrooksLean"})
    assert isinstance(hits, list)
    assert hits
    assert all(h["name"] == "BrooksLean" for h in hits)
    assert all(h["status"] == "external-verified" for h in hits)


def test_references_zone_not_established():
    hits = literature_search("RabernBook_FirstListBound", root=LIT)
    text = format_grounded_answer(
        commentary="Here are the book bounds.",
        claims=(),
        references=hits,
    )
    assert "Established (ledger):\n(nothing established)" in text
    assert "References (corpus):" in text
    assert "formalized (in-tree)" in text
    assert "Commentary:" in text
    refs = format_references_zone(hits)
    assert "stated only" not in refs
    assert "formalized" in refs


class _Scripted:
    def __init__(self, responses):
        self._responses = list(responses)

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        return self._responses.pop(0)


def test_agent_literature_search_fills_references_ledger_empty():
    reg = build_registry()
    model = _Scripted(
        [
            [ToolCall(id="1", name="literature_search", args={"query": "Rabern"})],
            AssistantText("Corpus hits above; none established this session."),
        ]
    )
    agent = Agent(reg, model)
    session = Session.create()
    from konigsberg_harness.models import UserMsg

    session.history.append(UserMsg("any results by Rabern?"))
    events = list(agent.step(session))
    final = next(e for e in events if isinstance(e, AssistantFinal))
    assert "References (corpus):" in final.text
    assert "formalized (in-tree)" in final.text
    assert "stated only — not yet proven" in final.text
    assert "external-verified" in final.text
    assert len(session.ledger.claims()) == 0
    assert len(final.claims) == 0
    assert final.references
