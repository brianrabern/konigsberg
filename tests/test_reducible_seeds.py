"""Rabern reducible-configuration seed catalogue."""
from __future__ import annotations

from konigsberg_empirical.fundamentals.codec import graph6_encode
from konigsberg_empirical.reduction.reducible import (
    BRIDGE_TAG,
    bridge_is_formalized,
    build_configuration,
    forbidden_configuration_statement,
)
from konigsberg_empirical.reduction.seeds import (
    load_reducible_seeds,
    next_unminted_seed,
    seeds_rederived_count,
)
from konigsberg_empirical.search.enumerate import parse_graph6
from konigsberg_harness.campaign import format_campaign_snapshot, next_step
from konigsberg_harness.ledger import mint_enumeration, mint_lean_proof
from konigsberg_harness.lemmas import LockedLemma


def test_seed_catalogue_loads_rabern_cores():
    seeds = load_reducible_seeds()
    assert len(seeds) >= 4
    names = {s.name for s in seeds}
    assert "CR_low_P3" in names
    assert "CR_low_C4" in names
    p3 = graph6_encode(3, [(0, 1), (1, 2)])
    c4 = graph6_encode(4, [(0, 1), (1, 2), (2, 3), (3, 0)])
    cores = {s.core for s in seeds}
    assert p3 in cores
    assert c4 in cores
    for seed in seeds:
        assert seed.degrees
        assert len(seed.degrees) >= 2
        assert seed.source


def test_next_unminted_seed_skips_rederived():
    seeds = load_reducible_seeds()
    first = seeds[0]
    second = seeds[1]
    assert next_unminted_seed(()) is first
    assert next_unminted_seed((first.core,)) is second
    all_cores = tuple(s.core for s in seeds)
    assert next_unminted_seed(all_cores) is None
    done, total = seeds_rederived_count(all_cores)
    assert done == total == len(seeds)


def test_next_unminted_seed_matches_canonical_core():
    from konigsberg_empirical.fundamentals.codec import canonical_graph6_str

    seeds = load_reducible_seeds()
    first = seeds[0]
    canon = canonical_graph6_str(first.core)
    assert next_unminted_seed((canon,)) is seeds[1]
    done, total = seeds_rederived_count((canon,))
    assert done == 1
    assert total == len(seeds)


def test_p3_and_p4_seed_specs_hit_at_d9():
    from konigsberg_harness.ledger import Claim
    from konigsberg_harness.tools.empirical_tools import reducible_configuration

    by_name = {s.name: s for s in load_reducible_seeds()}
    for name in ("CR_low_P3", "CR_low_P4"):
        seed = by_name[name]
        result = reducible_configuration(
            seed.core, degrees=list(seed.degrees), D=seed.D
        )
        assert isinstance(result, Claim), f"{name} {seed.degrees} D={seed.D} missed"


def test_bridge_is_formalized_in_corpus():
    assert bridge_is_formalized() is True


def test_bridge_is_formalized_fail_closed(tmp_path):
    missing = tmp_path / "absent.toml"
    assert bridge_is_formalized(missing) is False
    stated = tmp_path / "status.toml"
    stated.write_text(
        '[entry]\nname="BK_ReducibleOfFChoosable"\n'
        'citation="x"\narea="coloring"\n'
        "[[claims]]\n"
        'lean_name="Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable.reducible_of_fChoosable"\n'
        'status="stated"\nverified_at="0"\n',
        encoding="utf-8",
    )
    assert bridge_is_formalized(stated) is False


def test_forbidden_statement_drops_tag_when_formalized():
    seed = load_reducible_seeds()[0]
    graph = parse_graph6(seed.core)
    degrees = {i: int(d) for i, d in enumerate(seed.degrees)}
    config = build_configuration(graph, degrees, seed.D)
    stmt = forbidden_configuration_statement(seed.core, config, palette=4)
    assert BRIDGE_TAG not in stmt
    assert "FORBIDDEN CONFIGURATION" in stmt
    assert "H_BK" in stmt


def test_forbidden_statement_keeps_tag_if_unproved(monkeypatch):
    import sys

    redmod = sys.modules["konigsberg_empirical.reduction.reducible"]
    monkeypatch.setattr(redmod, "bridge_is_formalized", lambda status_path=None: False)
    seed = load_reducible_seeds()[0]
    graph = parse_graph6(seed.core)
    degrees = {i: int(d) for i, d in enumerate(seed.degrees)}
    config = build_configuration(graph, degrees, seed.D)
    stmt = forbidden_configuration_statement(seed.core, config, palette=4)
    assert BRIDGE_TAG in stmt


def test_staircase_cites_seed_after_bridge():
    proof = mint_lean_proof(
        "BK.reducible_of_fChoosable",
        axioms=("propext",),
        tool="lean_prove",
        durable=True,
    )
    lemma = LockedLemma(
        lean_name="BK.reducible_of_fChoosable",
        snippet="theorem reducible_of_fChoosable : True := trivial",
        durable=True,
    )
    nxt = next_step([proof], [lemma])
    first = load_reducible_seeds()[0]
    assert first.name in nxt
    assert first.core in nxt
    snap = format_campaign_snapshot([proof], [lemma])
    assert "seeds: 0/" in snap
    minted = mint_enumeration(
        f"FORBIDDEN CONFIGURATION core={first.core}, degree spec d_G={list(first.degrees)}",
        bound="palette<=4",
        exhaustive=True,
        tool="reducible_configuration",
    )
    snap2 = format_campaign_snapshot([proof, minted], [lemma])
    assert "seeds: 1/" in snap2
    assert load_reducible_seeds()[1].name in next_step([proof, minted], [lemma])
