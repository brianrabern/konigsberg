"""Guided discharging search: catalog cover + residual, not graph6 neighborhoods."""

from __future__ import annotations

from konigsberg_empirical.discharging.catalog import (
    CatalogEntry,
    cover_type,
    parse_catalog_text,
)
from konigsberg_empirical.discharging.engine import LocalType, verify_unavoidable
from konigsberg_empirical.discharging.search import (
    format_search_banner,
    frontier_statement,
    run_search,
)
from konigsberg_empirical.fundamentals.codec import graph6_encode
from konigsberg_harness.campaign import has_unavoidable
from konigsberg_harness.ledger import Claim, Ledger, mint_enumeration
from konigsberg_harness.tools.empirical_tools import DischargingResult
from konigsberg_harness.tools.registry import build_registry


def _edge() -> str:
    return graph6_encode(2, [(0, 1)])


def _triangle() -> str:
    return graph6_encode(3, [(0, 1), (0, 2), (1, 2)])


def _entry(core: str, *, proof: bool = True, name: str = "toy") -> CatalogEntry:
    tag = "offline" if proof else "3fold"
    n = 2 if core == _edge() else 3
    return CatalogEntry(
        name=name,
        core=core,
        degrees=tuple([8] * n),
        D=9,
        source=f"Rabern BK catalog ({tag}); test",
        note=f"reducers: {tag}",
        reducers=frozenset({tag}),
    )


def _forbidden(core: str) -> Claim:
    return mint_enumeration(
        f"FORBIDDEN CONFIGURATION (BK): core={core}, degree spec d_G=[8,8]",
        bound="palette<=4",
        exhaustive=True,
        tool="reducible_configuration",
    )


def test_catalog_parser_keeps_backslash_graph6():
    text = (
        '[[seed]]\n'
        'name = "rbk_fff7020e"\n'
        'source = "Rabern BK catalog (3fold); landon"\n'
        'core = "ES\\o"\n'
        "degrees = [8, 8, 8, 8, 8, 8]\n"
        "D = 9\n"
        'note = "reducers: 3fold"\n'
    )
    entries = parse_catalog_text(text)
    assert len(entries) == 1
    assert entries[0].core == "ES\\o"
    assert not entries[0].proof_grade


def test_full_catalog_loads_without_tomllib():
    from konigsberg_empirical.discharging.catalog import load_rabern_catalog

    cat = load_rabern_catalog()
    assert len(cat) > 1000
    assert any(e.proof_grade for e in cat)
    assert any(not e.proof_grade for e in cat)


def test_cover_type_edge_is_forced_in_every_center():
    edge = _edge()
    typ = LocalType(8, 0, 8)
    hit = cover_type(typ, (_entry(edge),), minted={edge}, minted_only=True)
    assert hit is not None
    assert hit.entry.core == edge
    assert hit.minted


def test_unminted_edge_is_not_a_minted_cover():
    edge = _edge()
    typ = LocalType(8, 1, 7)
    hit = cover_type(typ, (_entry(edge),), minted=set(), minted_only=True)
    assert hit is None
    hint = cover_type(typ, (_entry(edge),), minted=set(), minted_only=False)
    assert hint is not None and not hint.minted


def test_search_closes_on_minted_edge():
    edge = _edge()
    outcome = run_search(
        mu={8: -1, 9: -1},
        rules=[],
        forbidden=[],
        reducible_cores={edge},
        catalog=(_entry(edge),),
        max_iters=4,
    )
    assert outcome.status == "CLOSED"
    assert outcome.result.hit
    assert edge in outcome.forbidden
    assert outcome.result.ranked == ()


def test_search_does_not_launder_unminted_k2():
    edge = _edge()
    outcome = run_search(
        mu={8: -1, 9: -1},
        rules=[],
        forbidden=[],
        reducible_cores=set(),
        catalog=(_entry(edge),),
        max_iters=4,
    )
    assert outcome.status == "STUCK"
    assert not outcome.result.hit
    assert edge not in outcome.forbidden
    assert edge in outcome.unminted_covers
    assert outcome.result.ranked


def test_search_stuck_on_empty_catalog():
    outcome = run_search(
        mu={8: 0, 9: 1},
        rules=[],
        forbidden=[],
        reducible_cores=set(),
        catalog=(),
        max_iters=6,
    )
    assert outcome.status == "STUCK"
    assert outcome.result.ranked
    banner = format_search_banner(outcome)
    assert "DISCHARGING_SEARCH STUCK" in banner
    stmt = frontier_statement(outcome)
    assert "IRREDUCIBLE-FRONTIER" in stmt
    assert "FORBIDDEN CONFIGURATION" not in stmt.replace(
        "not a forbidden configuration", ""
    )
    assert "avoidable" not in stmt.lower().replace("unavoidable", "")


def test_tool_search_closes_and_mints_unavoidable():
    edge = _edge()
    reg = build_registry()
    ledger = Ledger()
    ledger.record(_forbidden(edge))
    reg.campaign_bind.ledger = ledger
    hit = reg.dispatch(
        "discharging_search",
        {"D": 9, "mu": {8: -1, 9: -1}, "rules": [], "forbidden": [], "max_iters": 4},
    )
    assert isinstance(hit, Claim)
    assert "UNAVOIDABLE" in hit.statement
    assert has_unavoidable([_forbidden(edge), hit])
    assert "DISCHARGING_SEARCH" in (reg.campaign_bind.last_search_banner or "")


def test_tool_search_mints_frontier_not_forbidden():
    tri = _triangle()
    reg = build_registry()
    ledger = Ledger()
    ledger.record(_forbidden(tri))
    bind = reg.campaign_bind
    bind.ledger = ledger
    out = reg.dispatch(
        "discharging_search",
        {
            "D": 9,
            "mu": {8: 0, 9: 1},
            "rules": [],
            "forbidden": [tri],
            "max_iters": 4,
        },
    )
    assert isinstance(out, Claim)
    assert "IRREDUCIBLE-FRONTIER" in out.statement
    assert "FORBIDDEN CONFIGURATION" not in out.statement
    assert bind.last_discharge_survivors
    cover = reg.dispatch(
        "discharging_cover",
        {"center_deg": 8, "n_high": 0, "n_low": 8},
    )
    assert isinstance(cover, str)
    assert "cover" in cover or "no catalog cover" in cover


def test_verify_still_silent_on_plain_miss():
    """discharging_unavoidable miss still mints nothing (search is the minter)."""
    from konigsberg_empirical.discharging import build_argument

    tri = _triangle()
    arg = build_argument(9, {8: -1, 9: -1}, [], [tri])
    result = verify_unavoidable(arg, reducible_cores={tri})
    assert not result.hit
    reg = build_registry()
    ledger = Ledger()
    ledger.record(_forbidden(tri))
    reg.campaign_bind.ledger = ledger
    miss = reg.dispatch(
        "discharging_unavoidable",
        {"D": 9, "mu": {8: -1, 9: -1}, "rules": [], "forbidden": [tri]},
    )
    assert isinstance(miss, DischargingResult)
