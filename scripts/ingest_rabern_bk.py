#!/usr/bin/env python3
"""ingest_rabern_bk — pull Landon Rabern's BK reducible-configuration catalog and
turn it into Konigsberg seeds.

Source: https://github.com/landon/landon.github.io/tree/master/graphdata/borodinkostochka
Each file lists graphs as upper-triangular adjacency bit-strings (row-major;
length L ⇒ n with n(n-1)/2 = L), split by the reducer that proved each config
reducible:  offline (ordinary choosability), AT (Alon–Tarsi), online
(paintability), 2fold / 3fold (k-fold list colouring).

Why the degree convention matters
---------------------------------
These are LOW-vertex configs of a minimal BK counterexample: ambient degree
d_G(v) = D-1. Feeding `reducible_configuration(core, degrees=[D-1]*n, D)` makes the
demand collapse to  f(v) = (D-1) - (d_G - deg_core) = deg_core(v)  — i.e.
DEGREE-CHOOSABILITY of the core. That is exactly Rabern's reducibility notion, so:
  * offline + AT configs  → our f-choosability engine should re-derive (~all),
  * online + k-fold       → stronger reducers; only the also-plain-choosable ones
                            re-derive (partial), the rest need fixer_breaker.

Outputs (next to the seeds module)
----------------------------------
  reducible_seeds.toml     engine-re-derivable seeds (offline+AT) → the staircase
  rabern_bk_catalog.toml   the FULL union (all reducers) → discharging set 𝒞

Run (on a machine with network; the harness sandbox blocks Claude's fetches, not
yours):
    uv run python scripts/ingest_rabern_bk.py            # fetch + write both files
    uv run python scripts/ingest_rabern_bk.py --validate # + re-derivation report
    uv run python scripts/ingest_rabern_bk.py --limit 50 # cap per file (smoke)
"""
from __future__ import annotations

import argparse
import hashlib
import math
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

_BASE = ("https://raw.githubusercontent.com/landon/landon.github.io/master/"
         "graphdata/borodinkostochka/")
REDUCERS = ("offline", "AT", "2fold", "3fold", "online")
# our f-choosability engine re-derives these two; the rest need stronger reducers
ENGINE_REDERIVABLE = {"offline", "AT"}
D_DEFAULT = 9  # live BK regime; low vertices have ambient degree D-1 = 8


def _seeds_dir() -> Path:
    return (Path(__file__).resolve().parent.parent / "empirical"
            / "konigsberg_empirical" / "reduction")


def fetch(reducer: str) -> list[str]:
    url = _BASE + reducer + ".txt"
    raw = urllib.request.urlopen(url, timeout=60).read()  # noqa: S310 (trusted host)
    for enc in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def decode_uppertri(bits: str) -> tuple[int, list[tuple[int, int]]] | None:
    L = len(bits)
    if not bits or any(ch not in "01" for ch in bits):
        return None
    n = (1 + math.isqrt(1 + 8 * L)) // 2
    if n * (n - 1) // 2 != L:
        return None
    edges: list[tuple[int, int]] = []
    idx = 0
    for i in range(n):
        for j in range(i + 1, n):
            if bits[idx] == "1":
                edges.append((i, j))
            idx += 1
    return n, edges


def to_canonical_graph6(n: int, edges: list[tuple[int, int]]) -> str | None:
    from konigsberg_empirical.fundamentals import codec

    try:
        g6 = codec.graph6_encode(n, [list(e) for e in edges])
        return codec.canonical_graph6_str(g6)
    except Exception:  # noqa: BLE001
        return None


def _name(canon: str) -> str:
    h = hashlib.sha1(canon.encode()).hexdigest()[:8]
    return f"rbk_{h}"


def build(limit: int | None) -> dict[str, dict]:
    """canonical graph6 -> {core, n, reducers:set, ...}."""
    recs: dict[str, dict] = {}
    reducer_of: dict[str, set[str]] = defaultdict(set)
    for reducer in REDUCERS:
        try:
            lines = fetch(reducer)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {reducer}: fetch failed ({e}); skipping", file=sys.stderr)
            continue
        kept = skipped = 0
        for i, bits in enumerate(lines):
            if limit is not None and kept >= limit:
                break
            dec = decode_uppertri(bits)
            if dec is None:
                skipped += 1
                continue
            n, edges = dec
            canon = to_canonical_graph6(n, edges)
            if canon is None:
                skipped += 1
                continue
            reducer_of[canon].add(reducer)
            recs.setdefault(canon, {"core": canon, "n": n})
            kept += 1
        print(f"  {reducer:8s} {kept:5d} configs"
              + (f"  ({skipped} skipped)" if skipped else ""))
    for canon, rset in reducer_of.items():
        recs[canon]["reducers"] = sorted(rset)
    return recs


def _row(rec: dict, D: int) -> str:
    n = rec["n"]
    reducers = rec.get("reducers", [])
    degrees = ", ".join(str(D - 1) for _ in range(n))
    name = _name(rec["core"])
    return (
        "[[seed]]\n"
        f'name = "{name}"\n'
        f'source = "Rabern BK catalog ({"/".join(reducers)}); landon.github.io/graphdata/borodinkostochka"\n'
        f'core = "{rec["core"]}"\n'
        f"degrees = [{degrees}]\n"
        f"D = {D}\n"
        f'note = "low-vertex config (ambient deg = D-1); demand = degree-choosability. reducers: {"/".join(reducers)}"\n'
    )


def write_toml(path: Path, recs: list[dict], D: int, header: str) -> None:
    body = [header, ""]
    for rec in sorted(recs, key=lambda r: (r["n"], r["core"])):
        body.append(_row(rec, D))
    path.write_text("\n".join(body), encoding="utf-8")
    print(f"  wrote {len(recs)} seeds → {path}")


def validate(seeds: list[dict], D: int, sample: int,
             max_n: int = 6, per_timeout: int = 20) -> None:
    """Spot-check re-derivation on SMALL configs, bounded per call.

    f-choosability is Π₂-hard, so large configs can hang; we sample only n ≤ max_n
    and cap each solve with SIGALRM. This is a fidelity check (decode + degree
    convention), not an exhaustive audit.
    """
    try:
        from konigsberg_harness.tools.registry import build_registry
        reg = build_registry()
    except Exception as e:  # noqa: BLE001
        print(f"validation skipped: {e}")
        return
    import random
    import signal

    small = [r for r in seeds if r["n"] <= max_n]
    if not small:
        print(f"validation: no seeds with n ≤ {max_n} to check")
        return
    picks = small if len(small) <= sample else random.sample(small, sample)

    class _Timeout(Exception):
        pass

    have_alarm = hasattr(signal, "SIGALRM")
    if have_alarm:
        signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(_Timeout()))

    hit = miss = to = err = 0
    print(f"\nvalidating {len(picks)} sampled seeds (n ≤ {max_n}); "
          f"offline/AT should ≈ all HIT:")
    for i, rec in enumerate(picks, 1):
        n = rec["n"]
        try:
            if have_alarm:
                signal.alarm(per_timeout)
            claim = reg.dispatch("reducible_configuration",
                                 {"core": rec["core"],
                                  "degrees": [D - 1] * n, "D": D})
            if have_alarm:
                signal.alarm(0)
            ok = "FORBIDDEN CONFIGURATION" in (getattr(claim, "statement", "") or "")
            hit += ok
            miss += (not ok)
            print(f"  [{i}/{len(picks)}] n={n} {'HIT ' if ok else 'miss'} {rec['core']}")
        except _Timeout:
            to += 1
            print(f"  [{i}/{len(picks)}] n={n} timeout(skip) {rec['core']}")
        except Exception as e:  # noqa: BLE001
            err += 1
            print(f"  [{i}/{len(picks)}] n={n} err: {e}")
        finally:
            if have_alarm:
                signal.alarm(0)
    tot = len(picks)
    print(f"\nHIT {hit}/{tot}   miss {miss}   timeout {to}   err {err}")
    print("(offline/AT ≈ all HIT ⇒ decode + degree convention are faithful)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ingest Rabern's BK reducible-config catalog.")
    p.add_argument("--limit", type=int, default=None, help="cap configs per file (smoke)")
    p.add_argument("--D", type=int, default=D_DEFAULT)
    p.add_argument("--validate", action="store_true",
                   help="run reducible_configuration on a sample and report HIT rate")
    p.add_argument("--sample", type=int, default=30, help="validation sample size")
    p.add_argument("--max-n", type=int, default=6,
                   help="validate only configs with n ≤ this (choosability is Π₂-hard)")
    p.add_argument("--per-timeout", type=int, default=20,
                   help="seconds cap per config during validation")
    p.add_argument("--seed-max-n", type=int, default=6,
                   help="max n for staircase seeds (keeps live solves fast; catalog unaffected)")
    args = p.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "empirical"))
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))

    print("fetching + decoding Rabern BK catalog…")
    recs = build(args.limit)
    if not recs:
        print("nothing ingested (all fetches failed?)", file=sys.stderr)
        return 1

    all_recs = list(recs.values())
    # Staircase seeds: engine-re-derivable AND small, so the hunt's
    # reducible_configuration calls stay fast (choosability is Π₂-hard; big configs
    # can hang the loop). Big configs live only in the discharging catalog below.
    rederivable = [r for r in all_recs
                   if ENGINE_REDERIVABLE.intersection(r.get("reducers", []))
                   and r["n"] <= args.seed_max_n]

    d = _seeds_dir()
    write_toml(
        d / "reducible_seeds.toml", rederivable, args.D,
        "# Rabern BK reducible-configuration seeds — ENGINE-RE-DERIVABLE, SMALL subset\n"
        f"# (offline / Alon–Tarsi, n ≤ {args.seed_max_n}). Consumed by campaign.py's\n"
        "# staircase — kept small so live reducible_configuration calls stay fast.\n"
        "# Full catalog (all sizes/reducers) is rabern_bk_catalog.toml. Generated by\n"
        "# scripts/ingest_rabern_bk.py from landon.github.io/graphdata/borodinkostochka.\n"
        "# Degrees assume low vertices (ambient = D-1); demand = degree-choosability.",
    )
    write_toml(
        d / "rabern_bk_catalog.toml", all_recs, args.D,
        "# Rabern BK reducible-configuration catalog — FULL union (all reducers:\n"
        "# offline/AT/online/2fold/3fold). Intended as the forbidden set 𝒞 for the\n"
        "# discharging engine. online/k-fold configs need fixer_breaker to re-derive,\n"
        "# not the plain f-choosability engine. Generated by scripts/ingest_rabern_bk.py.",
    )
    print(f"\ntotal distinct configs: {len(all_recs)}  "
          f"(engine-re-derivable offline/AT: {len(rederivable)})")

    if args.validate:
        validate(rederivable, args.D, args.sample,
                 max_n=args.max_n, per_timeout=args.per_timeout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
