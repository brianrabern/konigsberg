"""list_critical: Cranston–Rabern m-list-critical with index baked in."""
from __future__ import annotations

import ast
import re

import networkx as nx
import pytest
from konigsberg_empirical.coloring import choosability as ch
from konigsberg_harness.agent import Agent, AssistantFinal
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall, UserMsg
from konigsberg_harness.session import Session
from konigsberg_harness.tools.empirical_tools import list_critical, list_critical_definition
from konigsberg_harness.tools.registry import build_registry

needs_sat = pytest.mark.skipif(not ch.is_available(), reason="python-sat not installed")

_K4 = "C~"
_BAD_LIST_RE = re.compile(r"Bad 3-list (\[.*?\]) \(certificate-checked\)")


def _g6(G) -> str:
    return nx.to_graph6_bytes(G, header=False).decode().strip()


@needs_sat
def test_list_critical_k4_is_4_list_critical_with_bundle():
    """Regression: the warm-up failure — K₄ is 4-list-critical (not 3-choosable)."""
    claim = list_critical(_K4, 4)
    assert "IS 4-list-critical" in claim.statement
    assert "index=Cranston–Rabern" in claim.statement
    assert "k=3" in claim.statement  # baked index: m-1
    assert "Definition used:" not in claim.statement  # harness zone owns that
    assert claim.provenance.trust_root is TrustRoot.CERTIFICATE
    m = _BAD_LIST_RE.search(claim.statement)
    assert m is not None, claim.statement
    bad = ast.literal_eval(m.group(1))
    assert bad == [[0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2]]
    assert "all 6 edge deletions 3-choosable" in claim.statement
    assert "complete decision" in claim.statement


@needs_sat
def test_list_critical_3_choosable_graph_not_4_list_critical():
    path = _g6(nx.path_graph(4))
    claim = list_critical(path, 4)
    assert "NOT 4-list-critical" in claim.statement
    assert "3-choosable" in claim.statement or "is 3-" in claim.statement
    assert "index=Cranston–Rabern" in claim.statement


@needs_sat
def test_list_critical_registered_and_dispatches():
    reg = build_registry()
    assert "list_critical" in reg.names()
    specs = {s["name"]: s for s in reg.tool_specs()}
    assert specs["list_critical"]["input_schema"]["properties"].keys() >= {
        "graph6",
        "m",
        "palette",
    }
    claim = reg.dispatch("list_critical", {"graph6": _K4, "m": 4})
    assert "IS 4-list-critical" in claim.statement


def test_list_critical_definition_names_index():
    d = list_critical_definition(4)
    assert "4-list-critical" in d
    assert "not 3-choosable" in d
    assert "Cranston–Rabern" in d
    assert "KListCritical" in d


class _Scripted:
    def __init__(self, responses):
        self._responses = list(responses)

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        return self._responses.pop(0)


@needs_sat
def test_agent_list_critical_renders_definition_used_zone():
    reg = build_registry()
    model = _Scripted(
        [
            [ToolCall(id="1", name="list_critical", args={"graph6": _K4, "m": 4})],
            AssistantText("Yes — see the ledger."),
        ]
    )
    agent = Agent(reg, model)
    session = Session.create()
    session.history.append(UserMsg("is K4 4-list-critical?"))
    events = list(agent.step(session))
    final = next(e for e in events if isinstance(e, AssistantFinal))
    assert "Definition used:" in final.text
    assert "4-list-critical = not 3-choosable, edge-minimal" in final.text
    assert "IS 4-list-critical" in final.text
    assert len(final.definitions) == 1
