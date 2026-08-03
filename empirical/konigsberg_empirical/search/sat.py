"""SAT/ILP encodings for chromatic and list-chromatic queries beyond brute force."""
from __future__ import annotations


def sat_query(graph, k: int) -> bool:
    raise NotImplementedError


def ilp_query(graph, objective: str):
    raise NotImplementedError
