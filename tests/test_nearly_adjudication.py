"""Adjudication: clean-room fixability confirms MindTests nearly column on P_4.

See docs/handoff/NEARLY_COLORABLE_ADJUDICATION.md.
"""
from pathlib import Path

from konigsberg_empirical.coloring import fixer_breaker as fb
from konigsberg_empirical.coloring.fixability import (
    edge_colorable,
    enumerate_list_assignments,
    is_fixable,
    is_nearly_edge_colorable,
)

FIXTURES = Path(__file__).parent / "fixtures" / "rabern_graphs"


def _all_edge_lists_nonempty(graph, lists) -> bool:
    return all(lists[u] & lists[v] for u, v in graph.edges)


def _strict_nearly(graph, lists) -> bool:
    if edge_colorable(graph, lists):
        return False
    if not _all_edge_lists_nonempty(graph, lists):
        return False
    return is_nearly_edge_colorable(graph, lists)


def test_cleanroom_p4_good_nearly_win_true():
    g, labels = fb.load_dotgraph(FIXTURES / "P_4_good.graph")
    template, pot = fb.template_from_labels(g, labels)
    boards = []
    for cc in range(max(template.sizes), pot + 1):
        boards.extend(enumerate_list_assignments(template.sizes, cc))
    assert len(boards) == 28

    memo: dict = {}
    strict_nearly = [L for L in boards if _strict_nearly(g, L)]
    unfixable = [
        L for L in strict_nearly if not is_fixable(g, L, set().union(*L), _memo=memo)
    ]
    assert unfixable == [], "P_4_good: every strict-nearly board should be fixable"
    # and the engine agrees
    mind = fb.SuperSlimMind(g)
    mind.max_pot = pot
    mind.only_consider_nearly_colorable_boards = True
    assert mind.analyze(template) is True


def test_cleanroom_p4_bad_nearly_win_false():
    g, labels = fb.load_dotgraph(FIXTURES / "P_4_bad.graph")
    template, pot = fb.template_from_labels(g, labels)
    boards = []
    for cc in range(max(template.sizes), pot + 1):
        boards.extend(enumerate_list_assignments(template.sizes, cc))
    assert len(boards) == 40

    memo: dict = {}
    strict_nearly = [L for L in boards if _strict_nearly(g, L)]
    unfixable = [
        L for L in strict_nearly if not is_fixable(g, L, set().union(*L), _memo=memo)
    ]
    assert len(unfixable) > 0
    mind = fb.SuperSlimMind(g)
    mind.max_pot = pot
    mind.only_consider_nearly_colorable_boards = True
    assert mind.analyze(template) is False
