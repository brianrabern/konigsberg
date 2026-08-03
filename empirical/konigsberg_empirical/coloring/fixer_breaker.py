"""FixerBreaker: fixer-breaker game solver for online / list choosability.

Ported from Landon Rabern's engine. The differentiator — specialized and hard to
reproduce. Port validated against the .NET oracle via differential testing
(tests/differential) before vendor/ is retired.

Stretch goal: emit a winning-strategy certificate so results can be upgraded
from SOLVER to CERTIFICATE trust (see ledger.mint_certificate).
"""
from __future__ import annotations


def solve(graph, list_sizes):
    raise NotImplementedError("port FixerBreaker; validate vs vendor oracle")
