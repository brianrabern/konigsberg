"""Literature corpus index + retrieval.

Walks ``formal/Konigsberg/Literature/**/status.toml`` and merges
``EXTERNAL.toml``. This is a STRUCTURAL catalog for literature_search — not
goal-conditioned premise selection (see ``structural_index`` / ``rank_for_goal``).

Status vocabulary is preserved verbatim:
  formalized | stated | informal | external-verified
Retrieval never upgrades status and never mints ledger Claims.
"""
from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VALID_IN_TREE = frozenset({"formalized", "stated", "informal"})
VALID_EXTERNAL = frozenset({"external-verified"})


@dataclass(frozen=True)
class LiteratureHit:
    """One claim-level search result with mandatory status."""

    name: str
    citation: str
    area: str
    lean_name: str
    status: str
    provenance: str
    notes_excerpt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LiteratureEntry:
    name: str
    citation: str
    area: str
    claims: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    source: str = "in-tree"  # or "external"


def default_literature_root() -> Path:
    """Repo ``formal/Konigsberg/Literature`` relative to this package."""
    # .../harness/konigsberg_harness/context/library_map.py → repo root is parents[3]
    return Path(__file__).resolve().parents[3] / "formal" / "Konigsberg" / "Literature"


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"malformed TOML {path}: {e}") from e


def _load_status_toml(path: Path) -> LiteratureEntry:
    data = _read_toml(path)
    entry = data.get("entry")
    if not isinstance(entry, dict):
        raise TypeError(f"{path}: missing [entry] table")
    for key in ("name", "citation", "area"):
        if not entry.get(key):
            raise ValueError(f"{path}: [entry] missing '{key}'")
    claims_raw = data.get("claims", [])
    if not claims_raw:
        raise ValueError(f"{path}: no [[claims]]")
    claims: list[dict[str, Any]] = []
    for i, c in enumerate(claims_raw):
        if not isinstance(c, dict):
            raise TypeError(f"{path}: claims[{i}] not a table")
        for key in ("lean_name", "status", "verified_at"):
            if key not in c:
                raise ValueError(f"{path}: claims[{i}] missing '{key}'")
        status = c["status"]
        if status not in VALID_IN_TREE:
            raise ValueError(
                f"{path}: claims[{i}] invalid status {status!r} "
                f"(want {sorted(VALID_IN_TREE)})"
            )
        claims.append(
            {
                "lean_name": c["lean_name"],
                "status": status,  # verbatim
                "verified_at": c["verified_at"],
                "axioms": c.get("axioms"),
            }
        )
    notes_path = path.parent / "Notes.md"
    notes = notes_path.read_text(encoding="utf-8") if notes_path.is_file() else ""
    return LiteratureEntry(
        name=str(entry["name"]),
        citation=str(entry["citation"]),
        area=str(entry["area"]),
        claims=claims,
        notes=notes,
        source="in-tree",
    )


def _load_external_toml(path: Path) -> list[LiteratureEntry]:
    data = _read_toml(path)
    rows = data.get("external", [])
    if not isinstance(rows, list):
        raise TypeError(f"{path}: expected [[external]] array")
    out: list[LiteratureEntry] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError(f"{path}: external[{i}] not a table")
        for key in ("name", "citation", "area", "repo", "commit"):
            if not row.get(key):
                raise ValueError(f"{path}: external[{i}] missing '{key}'")
        claims_raw = row.get("claims", [])
        if not claims_raw:
            raise ValueError(f"{path}: external[{i}] has no claims")
        claims: list[dict[str, Any]] = []
        for j, c in enumerate(claims_raw):
            if not isinstance(c, dict):
                raise TypeError(f"{path}: external[{i}].claims[{j}] not a table")
            lean_name = c.get("lean_name")
            status = c.get("status", "external-verified")
            if not lean_name:
                raise ValueError(f"{path}: external[{i}].claims[{j}] missing lean_name")
            if status not in VALID_EXTERNAL:
                raise ValueError(
                    f"{path}: external[{i}].claims[{j}] status must be "
                    f"external-verified, got {status!r}"
                )
            claims.append(
                {
                    "lean_name": lean_name,
                    "status": status,  # verbatim
                    "statement": c.get("statement", ""),
                    "repo": row["repo"],
                    "commit": row["commit"],
                    "lean": row.get("lean", ""),
                    "mathlib": row.get("mathlib", ""),
                    "stage0_date": row.get("stage0_date", ""),
                }
            )
        out.append(
            LiteratureEntry(
                name=str(row["name"]),
                citation=str(row["citation"]),
                area=str(row["area"]),
                claims=claims,
                notes="",
                source="external",
            )
        )
    return out


def library_map(root: Path | str | None = None) -> list[LiteratureEntry]:
    """Parse every status.toml + EXTERNAL.toml into a serializable catalog."""
    lit = Path(root) if root is not None else default_literature_root()
    if not lit.is_dir():
        raise FileNotFoundError(f"literature root not found: {lit}")

    entries: list[LiteratureEntry] = []
    for status_path in sorted(lit.glob("**/status.toml")):
        entries.append(_load_status_toml(status_path))

    external_path = lit / "EXTERNAL.toml"
    if external_path.is_file():
        entries.extend(_load_external_toml(external_path))
    return entries


def _provenance(entry: LiteratureEntry, claim: dict[str, Any]) -> str:
    if entry.source == "external":
        parts = [
            f"repo={claim.get('repo', '')}",
            f"commit={claim.get('commit', '')}",
        ]
        if claim.get("lean"):
            parts.append(f"lean={claim['lean']}")
        if claim.get("mathlib"):
            parts.append(f"mathlib={claim['mathlib']}")
        return "; ".join(parts)
    return f"verified_at={claim.get('verified_at', '')}"


def _score(query: str, entry: LiteratureEntry, claim: dict[str, Any]) -> int | None:
    """Higher is better; None = no match. Exact/name beats citation/notes."""
    q = query.casefold().strip()
    if not q:
        return 0
    name = entry.name.casefold()
    lean = str(claim.get("lean_name", "")).casefold()
    cite = entry.citation.casefold()
    area = entry.area.casefold()
    notes = entry.notes.casefold()
    short = lean.rsplit(".", 1)[-1] if lean else ""

    if name == q or lean == q or short == q:
        return 100
    if q in name:
        return 80
    if q in lean or q in short:
        return 60
    if q in area:
        return 40
    if q in cite:
        return 30
    if q in notes:
        return 10
    return None


def literature_search(
    query: str,
    *,
    area: str | None = None,
    status: str | None = None,
    root: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Substring search over the corpus. Returns status-bearing hit dicts.

    Does NOT mint Claims. Status is carried verbatim from disk.
    """
    catalog = library_map(root)
    area_f = area.casefold() if area else None
    status_f = status  # exact match on status vocabulary
    scored: list[tuple[int, LiteratureHit]] = []

    for entry in catalog:
        if area_f is not None and entry.area.casefold() != area_f:
            continue
        for claim in entry.claims:
            if status_f is not None and claim["status"] != status_f:
                continue
            score = _score(query, entry, claim)
            if score is None:
                continue
            hit = LiteratureHit(
                name=entry.name,
                citation=entry.citation,
                area=entry.area,
                lean_name=claim["lean_name"],
                status=claim["status"],  # verbatim — never upgraded
                provenance=_provenance(entry, claim),
            )
            scored.append((score, hit))

    scored.sort(key=lambda p: (-p[0], p[1].name, p[1].lean_name))
    return [h.to_dict() for _, h in scored]


def structural_index(library_root: str) -> dict:
    """Cheap, deterministic index: namespaces, signatures, def-use edges."""
    raise NotImplementedError


def rank_for_goal(goal_state: str, token_budget: int) -> list[str]:
    """Premise selection. Research subproblem — see module docstring."""
    raise NotImplementedError
