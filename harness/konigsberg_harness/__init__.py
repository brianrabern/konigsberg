"""Konigsberg agent harness — the core tier.

Owns the agent loop, the tool registry, context surfacing, and the epistemic
ledger. Talks to the formal (Lean) and empirical (Python) tiers only through
tools; those two tiers never import each other.
"""
from . import ledger

__all__ = ["ledger"]
