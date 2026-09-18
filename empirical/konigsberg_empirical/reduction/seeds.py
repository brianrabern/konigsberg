"""Rabern forbidden-configuration seeds (catalogue, not Claims)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class ReducibleSeed:
    name: str
    source: str
    core: str
    degrees: tuple[int, ...]
    D: int | None
    note: str = ""


def _toml_path() -> Path:
    return Path(__file__).resolve().parent / "reducible_seeds.toml"


@lru_cache(maxsize=1)
def load_reducible_seeds() -> tuple[ReducibleSeed, ...]:
    path = _toml_path()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    seeds: list[ReducibleSeed] = []
    for row in data.get("seed", []):
        degrees = row["degrees"]
        seeds.append(
            ReducibleSeed(
                name=str(row["name"]),
                source=str(row["source"]),
                core=str(row["core"]),
                degrees=tuple(int(d) for d in degrees),
                D=int(row["D"]) if row.get("D") is not None else None,
                note=str(row.get("note", "")),
            )
        )
    return tuple(seeds)


def next_unminted_seed(cores: tuple[str, ...] | list[str]) -> ReducibleSeed | None:
    """First catalogue seed whose graph6 is not yet a forbidden core on the ledger."""
    have = set(cores)
    for seed in load_reducible_seeds():
        if seed.core not in have:
            return seed
    return None


def seeds_rederived_count(cores: tuple[str, ...] | list[str]) -> tuple[int, int]:
    have = set(cores)
    seeds = load_reducible_seeds()
    done = sum(1 for s in seeds if s.core in have)
    return done, len(seeds)
