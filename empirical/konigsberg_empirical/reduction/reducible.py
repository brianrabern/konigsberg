"""BK reducibility via f-choosability of a configuration core.

Pure Python — reuses konigsberg_empirical.coloring.choosability (CEGAR/SAT).
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from ..coloring import choosability as _ch
from ..core import Graph
from ..sufficient_only import assert_sufficient_only

BRIDGE_LEMMA = "BK.reducible_of_fChoosable"
BRIDGE_TAG = f"[conditional on reducibility bridge lemma {BRIDGE_LEMMA}]"

_BRIDGE_STATUS = (
    Path(__file__).resolve().parents[3]
    / "formal"
    / "Konigsberg"
    / "Literature"
    / "Coloring"
    / "BK_ReducibleOfFChoosable"
    / "status.toml"
)


def bridge_is_formalized(status_path: Path | None = None) -> bool:
    """True iff Literature records ``reducible_of_fChoosable`` as ``formalized``.

    Fail-closed: missing file, unreadable TOML, or any other status keeps the
    HIT tag. The empirical engine does not upgrade trust.
    """
    path = status_path if status_path is not None else _BRIDGE_STATUS
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, TypeError):
        return False
    for claim in data.get("claims", []):
        if not isinstance(claim, dict):
            continue
        if "reducible_of_fChoosable" in str(claim.get("lean_name", "")):
            return claim.get("status") == "formalized"
    return False

MAX_CORE_VERTICES = 12
MAX_PALETTE = 72  # |K|≤12, f≤6 ⇒ palette≤72


@dataclass(frozen=True)
class Configuration:
    """A BK local configuration: core K + derived slack lists f."""

    core: Graph
    f: dict[int, int]  # worst-case list size per core vertex, ≥ 1 when in scope
    degree_spec: dict[int, int]  # d_G(v) in the ambient graph
    D: int | None  # None ⇒ low-vertex / D-uniform


@dataclass(frozen=True)
class ReduceResult:
    """Outcome of reducibility testing (sufficient-only)."""

    hit: bool
    out_of_scope: bool = False
    reason: str = ""
    palette: int = 0
    bad_list: list[set[int]] | None = None


class ToolBudgetExceeded(ValueError):
    """Raised when a configuration would exceed safe choosability search bounds."""


def _validate_degree_spec(core: Graph, degree_spec: dict[int, int]) -> None:
    n = core.n
    if set(degree_spec) != set(range(n)):
        missing = [v for v in range(n) if v not in degree_spec]
        raise ValueError(f"degree spec must cover vertices 0..{n - 1}; missing {missing}")


def build_configuration(
    core: Graph,
    degree_spec: dict[int, int],
    D: int | None = None,
) -> Configuration:
    """Derive f from (core, degree_spec, D). Never accept hand-supplied f."""
    _validate_degree_spec(core, degree_spec)
    deg_k = {v: core.degree(v) for v in range(core.n)}

    if D is None:
        degs = set(degree_spec.values())
        if len(degs) != 1:
            raise ValueError(
                "low-vertex / D-uniform mode requires all d_G(v) equal "
                f"(got {sorted(degs)})"
            )
        f = {v: deg_k[v] for v in range(core.n)}
        return Configuration(core=core, f=f, degree_spec=dict(degree_spec), D=None)

    for v in range(core.n):
        dg = degree_spec[v]
        if not (deg_k[v] <= dg <= D):
            raise ValueError(
                f"vertex {v}: need deg_K({v})={deg_k[v]} ≤ d_G(v)={dg} ≤ D={D}"
            )
    f = {v: (D - 1) - degree_spec[v] + deg_k[v] for v in range(core.n)}
    return Configuration(core=core, f=f, degree_spec=dict(degree_spec), D=D)


def reducible(config: Configuration) -> ReduceResult:
    """Test f-choosability of the core (sufficient-only reducibility).

    HIT  — no bad f-list to complete palette ⇒ core f-choosable ⇒ forbidden.
    MISS — bad f-list found, or out of scope; proves nothing about reducibility.
    """
    core = config.core
    if core.n > MAX_CORE_VERTICES:
        raise ToolBudgetExceeded(
            f"core has {core.n} vertices (limit {MAX_CORE_VERTICES})"
        )

    if any(fv <= 0 for fv in config.f.values()):
        return ReduceResult(
            hit=False,
            out_of_scope=True,
            reason="some f(v) ≤ 0 (core vertex has no slack for this method)",
        )

    if not _ch.is_available():
        raise RuntimeError("pysat not installed (choosability backend unavailable)")

    palette = _ch.complete_palette_f(core, config.f)
    if palette > MAX_PALETTE:
        raise ToolBudgetExceeded(
            f"palette {palette} exceeds limit {MAX_PALETTE} "
            f"(max f={max(config.f.values())}, n={core.n})"
        )

    bad = _ch.find_bad_list_f(core, config.f, palette=palette)
    if bad is not None:
        return ReduceResult(
            hit=False,
            reason="bad f-list found (method inconclusive; proves nothing)",
            palette=palette,
            bad_list=bad,
        )
    return ReduceResult(hit=True, palette=palette)


def format_degree_spec(degree_spec: dict[int, int]) -> str:
    return "{" + ", ".join(f"{v}:{degree_spec[v]}" for v in sorted(degree_spec)) + "}"


def format_f(f: dict[int, int]) -> str:
    return "{" + ", ".join(f"{v}:{f[v]}" for v in sorted(f)) + "}"


def forbidden_configuration_statement(
    graph6: str,
    config: Configuration,
    *,
    palette: int,
) -> str:
    """Human-facing forbidden-configuration Claim string (H_BK explicit)."""
    d_part = "D-uniform" if config.D is None else f"Δ={config.D}"
    stmt = (
        "FORBIDDEN CONFIGURATION (BK minimal counterexample, H_BK: Δ=D≥9, "
        f"K_D-free, D-critical; {d_part}): "
        f"core={graph6}, degree spec d_G={format_degree_spec(config.degree_spec)}, "
        f"slack f={format_f(config.f)}; core is f-choosable "
        f"(exhaustive to palette P={palette}) ⇒ reducible ⇒ absent from every "
        "minimal counterexample."
    )
    if not bridge_is_formalized():
        stmt = f"{stmt} {BRIDGE_TAG}"
    return assert_sufficient_only(stmt)
