"""FixerBreaker fingerprints from WebGraphs UnitTests/MindTests.cs.

Strict nearly-colorable (all edge lists nonempty) — see
docs/handoff/NEARLY_COLORABLE_ADJUDICATION.md.
"""
from pathlib import Path

import pytest
from konigsberg_empirical.coloring import fixer_breaker as fb
from konigsberg_empirical.coloring.bit_assignments import generate_assignments

FIXTURES = Path(__file__).parent / "fixtures" / "rabern_graphs"

# (graph file, TotalBoards, fixer wins, nearly_win) — MindTests column
FINGERPRINTS = [
    ("P_4_good.graph", 28, False, True),
    ("P_4_bad.graph", 40, False, False),
    ("long_3_claw_very_good.graph", 2336, True, None),
    ("long_3_claw_good.graph", 3488, False, True),
    ("long_3_claw_bad.graph", 5216, False, False),
]


def test_p4_good_template_sizes():
    graph, labels = fb.load_dotgraph(FIXTURES / "P_4_good.graph")
    assert labels == [2, 4, 4, 2]
    assert sorted(graph.edges) == [(0, 1), (1, 2), (2, 3)]
    template, pot = fb.template_from_labels(graph, labels)
    assert pot == 4
    assert template.sizes == [3, 2, 2, 3]


def test_generate_p4_good_board_counts():
    sizes = [3, 2, 2, 3]
    total = len(generate_assignments(sizes, 3)) + len(generate_assignments(sizes, 4))
    assert total == 28


@pytest.mark.parametrize(
    "name,total,should_win,_",
    [f for f in FINGERPRINTS if "long_3_claw" not in f[0]],
)
def test_total_boards_and_outright_win_fast(name, total, should_win, _):
    graph, labels = fb.load_dotgraph(FIXTURES / name)
    template, pot = fb.template_from_labels(graph, labels)
    mind = fb.SuperSlimMind(graph)
    mind.max_pot = pot
    win = mind.analyze(template)
    assert mind.total_boards == total
    assert win is should_win


@pytest.mark.slow
@pytest.mark.parametrize(
    "name,total,should_win,_",
    [f for f in FINGERPRINTS if "long_3_claw" in f[0]],
)
def test_total_boards_and_outright_win_slow(name, total, should_win, _):
    graph, labels = fb.load_dotgraph(FIXTURES / name)
    template, pot = fb.template_from_labels(graph, labels)
    mind = fb.SuperSlimMind(graph)
    mind.max_pot = pot
    win = mind.analyze(template)
    assert mind.total_boards == total
    assert win is should_win


@pytest.mark.parametrize(
    "name,total,_,nearly",
    [f for f in FINGERPRINTS if f[3] is not None and "long_3_claw" not in f[0]],
)
def test_nearly_colorable_win_fast(name, total, _, nearly):
    graph, labels = fb.load_dotgraph(FIXTURES / name)
    template, pot = fb.template_from_labels(graph, labels)
    mind = fb.SuperSlimMind(graph)
    mind.max_pot = pot
    mind.only_consider_nearly_colorable_boards = True
    assert mind.analyze(template) is nearly


@pytest.mark.slow
@pytest.mark.parametrize(
    "name,total,_,nearly",
    [f for f in FINGERPRINTS if f[3] is not None and "long_3_claw" in f[0]],
)
def test_nearly_colorable_win_slow(name, total, _, nearly):
    graph, labels = fb.load_dotgraph(FIXTURES / name)
    template, pot = fb.template_from_labels(graph, labels)
    mind = fb.SuperSlimMind(graph)
    mind.max_pot = pot
    mind.only_consider_nearly_colorable_boards = True
    assert mind.analyze(template) is nearly
