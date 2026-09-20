"""Rabern BK catalog loader + mechanical cover of v1 local types.

``rabern_bk_catalog.toml`` is not valid TOML (graph6 cores contain raw
backslashes). Load with a line parser. Cover is ``core_forced_in_type``,
not induced-subgraph-of-graph6: v1 survivors are degree signatures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..core import Graph
from ..search.enumerate import parse_graph6
from .engine import LocalType, core_forced_in_type

_PROOF_GRADE = frozenset({"offline", "at"})
_GRAPH_CACHE: dict[str, Graph | None] = {}


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    core: str
    degrees: tuple[int, ...]
    D: int | None
    source: str
    note: str
    reducers: frozenset[str]

    @property
    def proof_grade(self) -> bool:
        return bool(self.reducers & _PROOF_GRADE)

    @property
    def n(self) -> int:
        if self.degrees:
            return len(self.degrees)
        g = catalog_graph(self.core)
        return 0 if g is None else g.n


@dataclass(frozen=True)
class CatalogCover:
    entry: CatalogEntry
    minted: bool = False


def _catalog_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "reduction"
        / "rabern_bk_catalog.toml"
    )


def _unquote(raw: str) -> str:
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in {'"', "'"}:
        return s[1:-1]
    return s


def _reducers_of(source: str, note: str) -> frozenset[str]:
    m = re.search(r"catalog \(([^)]+)\)", source)
    blob = m.group(1) if m else ""
    if not blob:
        m2 = re.search(r"reducers:\s*(\S+)", note)
        blob = m2.group(1) if m2 else ""
    return frozenset(p.strip().lower() for p in blob.split("/") if p.strip())


def _entry_from_fields(fields: dict[str, str]) -> CatalogEntry | None:
    core = fields.get("core", "")
    if not core:
        return None
    deg_raw = fields.get("degrees", "")
    degrees = tuple(int(x) for x in re.findall(r"-?\d+", deg_raw))
    d_raw = fields.get("D", "").strip()
    d_val = int(d_raw) if d_raw.isdigit() else None
    source = fields.get("source", "")
    note = fields.get("note", "")
    return CatalogEntry(
        name=fields.get("name", ""),
        core=core,
        degrees=degrees,
        D=d_val,
        source=source,
        note=note,
        reducers=_reducers_of(source, note),
    )


def parse_catalog_text(text: str) -> tuple[CatalogEntry, ...]:
    entries: list[CatalogEntry] = []
    fields: dict[str, str] = {}

    def flush() -> None:
        entry = _entry_from_fields(fields)
        if entry is not None:
            entries.append(entry)

    for line in text.splitlines():
        s = line.strip()
        if s == "[[seed]]":
            flush()
            fields = {}
            continue
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, raw = s.partition("=")
        fields[key.strip()] = _unquote(raw)
    flush()
    return tuple(entries)


@lru_cache(maxsize=1)
def load_rabern_catalog() -> tuple[CatalogEntry, ...]:
    path = _catalog_path()
    if not path.is_file():
        return ()
    return parse_catalog_text(path.read_text(encoding="utf-8"))


def entries_from_cores(
    cores: set[str] | frozenset[str] | list[str],
    *,
    proof_grade: bool = True,
) -> tuple[CatalogEntry, ...]:
    """Treat already-minted ledger cores as cover candidates."""
    tag = "offline" if proof_grade else "3fold"
    out: list[CatalogEntry] = []
    for core in cores:
        graph = catalog_graph(core)
        if graph is None:
            continue
        out.append(
            CatalogEntry(
                name="ledger",
                core=core,
                degrees=tuple([8] * graph.n),
                D=9,
                source=f"Rabern BK catalog ({tag}); ledger",
                note=f"reducers: {tag}",
                reducers=frozenset({tag}),
            )
        )
    return tuple(out)


def catalog_graph(core: str) -> Graph | None:
    if core not in _GRAPH_CACHE:
        try:
            _GRAPH_CACHE[core] = parse_graph6(core)
        except (ValueError, TypeError, KeyError):
            _GRAPH_CACHE[core] = None
    return _GRAPH_CACHE[core]


def covers_for_type(
    typ: LocalType,
    catalog: tuple[CatalogEntry, ...] | list[CatalogEntry],
    *,
    minted: set[str] | frozenset[str] | None = None,
) -> tuple[CatalogCover, ...]:
    """Catalog entries forced into every closed neighborhood of ``typ``."""
    have = minted or frozenset()
    hits: list[CatalogCover] = []
    cap = typ.center_deg + 1
    for entry in catalog:
        if entry.n > cap:
            continue
        graph = catalog_graph(entry.core)
        if graph is None:
            continue
        if graph.n > cap:
            continue
        if core_forced_in_type(graph, typ):
            hits.append(CatalogCover(entry, minted=entry.core in have))
    hits.sort(
        key=lambda h: (
            0 if h.entry.proof_grade else 1,
            0 if h.minted else 1,
            h.entry.n,
            h.entry.name,
        )
    )
    return tuple(hits)


def cover_type(
    typ: LocalType,
    catalog: tuple[CatalogEntry, ...] | list[CatalogEntry],
    *,
    minted: set[str] | frozenset[str] | None = None,
    minted_only: bool = False,
) -> CatalogCover | None:
    """Best cover of ``typ``, or None.

    Prefer proof-grade (offline/AT), then already-minted, then small n.
    ``minted_only`` restricts to ledger cores — the only covers a search
    may add to 𝒞 (unminted catalog hits are hints, not UNAVOIDABLE fuel).
    """
    hits = covers_for_type(typ, catalog, minted=minted)
    if minted_only:
        hits = tuple(h for h in hits if h.minted)
    return hits[0] if hits else None
