"""Alon-Tarsi / Combinatorial Nullstellensatz.

The Alon-Tarsi number bounds list-chromatic number. Crucially, an orientation
with #even != #odd Eulerian subgraphs is a FINITE, INDEPENDENTLY RE-CHECKABLE
certificate — so this solver should return a certificate and we verify it,
yielding CERTIFICATE trust rather than mere SOLVER trust.
"""
from __future__ import annotations


def certificate(graph):
    """Return a re-checkable Alon-Tarsi orientation certificate, or None."""
    raise NotImplementedError


def verify_certificate(graph, cert) -> bool:
    """Independently re-check a certificate. Cheap relative to finding it."""
    raise NotImplementedError
