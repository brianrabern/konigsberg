"""Differential: Python FixerBreaker vs committed .NET oracle corpus.

No dotnet required at test time — pins against recorded fixtures.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from konigsberg_empirical.coloring.fixer_breaker import SuperSlimMind, Template
from konigsberg_empirical.core import Graph

CORPUS = Path(__file__).parent / "fixtures" / "fixer_breaker_corpus.jsonl"


def _load_corpus() -> list[dict]:
    if not CORPUS.exists():
        return []
    return [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]


CORPUS_RECORDS = _load_corpus()


pytestmark = pytest.mark.skipif(
    not CORPUS_RECORDS, reason="fixer_breaker_corpus.jsonl not generated yet"
)


def _run_python(rec: dict) -> tuple[int, bool, bool | None]:
    graph = Graph.of(rec["n"], [tuple(e) for e in rec["edges"]])
    mind = SuperSlimMind(graph)
    mind.max_pot = rec["max_pot"]
    win = mind.analyze(Template(sizes=list(rec["sizes"])))
    nearly: bool | None = None
    if not win:
        mind2 = SuperSlimMind(graph)
        mind2.max_pot = rec["max_pot"]
        mind2.only_consider_nearly_colorable_boards = True
        nearly = mind2.analyze(Template(sizes=list(rec["sizes"])))
    return mind.total_boards, win, nearly


@pytest.mark.parametrize("rec", CORPUS_RECORDS, ids=lambda r: f"n{r['n']}_p{r['max_pot']}_{r['graph6']}")
def test_python_matches_oracle_record(rec: dict):
    total, win, nearly = _run_python(rec)
    assert total == rec["total_boards"], f"total_boards mismatch on {rec['graph6']}"
    assert win is rec["win"], f"win mismatch on {rec['graph6']}"
    assert nearly == rec.get("nearly_win"), f"nearly_win mismatch on {rec['graph6']}"
