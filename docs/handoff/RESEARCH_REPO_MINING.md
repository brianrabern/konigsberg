# Mining Landon Rabern's research corpus

*`github.com/landon/Research` (~50 project directories) is a systematic source
for Konigsberg — definitions, theorems, solver code, datasets, and open
conjectures, almost all coloring/BK. This is the plan for ingesting it over time.
Not a one-off; a standing pipeline.*

## Licensing: no barrier

`LICENSE.md` is a **public-domain dedication** ("free and unencumbered ideas
released into the public domain … copy, modify, use, sell, or distribute … for
any purpose"). Everything in the repo is public domain. Nothing here needs
permission to ingest, and it retroactively confirms the WebGraphs/oracle reuse.
Record provenance in the ledger anyway (source = this repo) — for traceability,
not permission.

## Three ingestion pathways

Each artifact type maps to a Konigsberg tier:

1. **LaTeX / notes → `Literature` (statements-first).** Extract `\begin{theorem
   |lemma|definition}` blocks; each becomes a `Literature/Coloring/<Label>/`
   entry keyed to Landon's own label (`Statements.lean` typechecks with `sorry`;
   `status.toml` cites the repo path). `lean_search`/Loogle first to avoid
   reproving mathlib.
2. **C# / solver code → empirical tier + differential oracle.** Port or wrap as
   tools; validate by the same differential discipline as WebGraphs (unit-test
   fingerprints → committed corpus). Faithfulness verified, never assumed.
3. **Datasets / conjectures → empirical targets.** Graph datasets are
   differential-test seeds and BK reducible-config corpora; open conjectures are
   ready-made inputs for `counterexample_search` / `choosability_refute` (refute
   cheaply before anyone formalizes).

## Priority tiers (triaged by directory name — verify by inspection)

### Tier 1 — BK / choosability core (north-star)
| Dir | Likely content | Pathway |
|---|---|---|
| `bk`, `BKRecolor`, `fractional BK`, `choiceBKlarge` | Borodin–Kostochka core, recoloring, fractional/choice variants | Literature + data |
| `fixable`, `FixerDelta3` | **"Edge-coloring via fixable subgraphs"** — DEFINES the fixer-breaker game + nearly-colorable refinement | Literature (authoritative defs) — settles the fixer-breaker/nearly-colorable semantics |
| `4ListCriticalEdgeBound`, `ImprovedEdgeBound`, `OreVizing` | The list-critical edge-bound program (`BasicIrreducible` → these) | Literature |
| `DeltaCritical`, `DenseNeighborhoods`, `transitive` | Δ-critical small high-vertex cliques; dense-nbhd; vertex-transitive (the `gct` endgame) | Literature |
| `line graph`, `list edge coloring complete`, `HiltonZhao`, `goldberg` | edge/line-graph choosability, Hilton–Zhao, Goldberg | Literature (BK-for-line-graphs) |

### Tier 2 — methods / foundations
`gct`, `notes`, `thesis`, `Defense` (the books + dissertation — definitional
source, `gct` already reviewed); `transversal`, `hall`, `har` (independent
transversals / Hall / Haxell); `PlanarAT`, `generalized_orientations`,
`MixedChoosables` (Alon–Tarsi / orientations — validate the AT port);
`HypergraphKernelMagic` (kernel magic); `brooks improvement`, `simple brooks`;
`reedbound`; `partitioning and coloring`, `partition note`, `destroying`;
`multifold` (k-fold coloring / the 2-fold, 3-fold BK data).

### Tier 3 — data / tooling / candidates
`Graph Data` (datasets → differential seeds + reducible-config corpora);
`Tarpits` (tarpit enumeration — part of the WebGraphs word-game machinery);
`conjectures` (→ `counterexample_search` targets).

### Skip / non-math (name-triaged)
`jobs`, `talks`, `teaching`, `study`, `block proposal`, `singularities…mindspace`,
`danger` (Brian's semantic-paradox paper — different project), plus a long tail
of coded-name dirs (`demon`, `frons`, `flag`, `entropy`, `egt`, `mules`,
`stolid`, `verboten`, `walk`, `56`, `one`, `two`, …) — inspect before deciding;
many are scratch.

## Highest-value starts

1. **`fixable`** — the paper that *defines* the fixer-breaker game and the
   nearly-colorable refinement (arXiv 1507.05600). Ingesting it turns the
   nearly-colorable adjudication from "clean-room + published data" into "matches
   the author's stated definition", and pins the fixer_breaker port's semantics.
2. **`4ListCriticalEdgeBound` / `ImprovedEdgeBound`** — the edge-lower-bound
   theorems downstream of `BasicIrreducible`; the first substantial `Literature`
   entries once f-irreducibility is defined in Lean.
3. **`Graph Data`** — widen the differential corpus and seed the BK
   reducible-config search.
4. **`conjectures`** — point the empirical refutation tools at them immediately;
   cheap wins, and exactly what the "refutation before proof" tier is for.

## How to run it (mechanically)

- A small extractor: pull `\label{…}` + statement bodies from each `.tex`, emit
  skeleton `Literature/Coloring/<Label>/` entries (`Statements.lean` +
  `status.toml` with `status = "informal"` until the statement is Lean-ified).
  This makes the corpus enumerable and tracked without formalizing everything.
- Keep every entry's `status.toml` citing the exact repo path + commit, so
  provenance is traceable even though licensing is unrestricted.
- Triage is by directory name here; **confirm contents before ingesting** — the
  coded-name dirs especially.

## Caveat

Categorization above is from directory names only. The first real step is a
content pass (cheap: fetch each dir's file list + any `.tex`/README) to confirm
tiers and spot the highest-signal theorems. Do that before committing entries.
