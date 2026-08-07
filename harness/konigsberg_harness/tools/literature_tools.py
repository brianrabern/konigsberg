"""Literature corpus tools. Retrieval only — never mints Claims."""
from __future__ import annotations

from typing import Any

from ..context.library_map import literature_search as _search


def literature_search(
    query: str,
    area: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Search the Literature corpus (status.toml + EXTERNAL.toml).

    Returns claim-level records with mandatory ``status`` (formalized / stated /
    informal / external-verified) and provenance. Does **not** mint ledger Claims —
    catalog lookup ≠ establishment this session.
    """
    return _search(query, area=area, status=status)
