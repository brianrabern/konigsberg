"""The empirical <-> formal seam. The one place the two tiers meet.

A bug here looks AUTHORITATIVE ("decide confirmed it"), so the encoder gets the
same rigor as the solver port: round-trip property tests in CI
(Python graph -> Lean -> read back -> assert isomorphic). See tests/differential.

Honest scope note: `decide` over SimpleGraph blows up in the kernel at small n,
and native_decide is not whitelisted. So this bridge's formal-checking path is
useful only for TINY graphs; for anything larger its value is an empirical
cross-check, minted as ENUMERATION, not as a Lean proof.
"""
from __future__ import annotations


def export_graph_to_lean(graph) -> str:
    """Python graph -> `SimpleGraph (Fin n)` Lean source for decide-based checks."""
    raise NotImplementedError


def roundtrip_check(graph) -> bool:
    """Property test hook: export, re-import, assert isomorphic. Run in CI."""
    raise NotImplementedError
