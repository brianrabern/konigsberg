# The coloring book as the formal-tier spine

*Landon Rabern's "Basic Graph Coloring" (his unfinished book,
`landon.github.io/notes/BasicGraphColoring.pdf`) is the canonical reference that
organizes the formal tier and the Literature corpus. Definitions drive
`Areas/Coloring`; theorems become `Literature` statement-entries in his labels;
the nullstellensatz chapter is the definitional reference for the Alon–Tarsi
port. This document maps the book onto the repo and records the alignment and the
one correction it forces.*

## Why this book, specifically

It is the theory in the author's own framing, in dependency order, at exactly the
scope Konigsberg targets (list coloring → prescribed list sizes → nullstellensatz
→ independent transversals → edge coloring → BK). Formalizing *his* definitions
keeps the whole stack — formal library, literature statements, and the empirical
AT/fixer-breaker ports — speaking one vocabulary.

## Definitional alignment (`Areas/Coloring/Basic.lean`)

| Book definition | Lean status |
|---|---|
| *list assignment* `L : V → 𝒫(colors)` | `ListAssignment` ✓ |
| *L-colorable* (`∃ c_v ∈ L(v)`, proper) | `ListColorable` ✓ **matches verbatim** |
| *f-choosable* (colorable from every assignment of the prescribed sizes) | `FChoosable` ✓ |
| k-choosable / chₗ / degree-choosable | `Choosable` / `choiceNumber` / `DegreeChoosable` ✓ |
| **G-numbering**: `f : V → ℤ`, `f(v) ≤ d(v)+1` | **ADD** (trivial def) |
| **`f_H` restriction**: `f_H(v) = f(v) − (d_G(v) − d_H(v))` on induced `H` | **ADD** (needs `SimpleGraph.induce`) |
| **f-reducible / f-irreducible** (to a nonempty induced subgraph) | **ADD — primary criticality notion** |
| orientation, out-degree `d⁺`, acyclic, *kernel*, *kernel-perfect*, *superoriented* | ADD as the orientation theorems need them |
| *graph polynomial* `p_G`, coeff `p_k(G) = |DE|−|DO| = |EE|−|EO|` | ties to `empirical/.../polynomials.py` + `alon_tarsi.py` |

### The correction this forces

The book's criticality is **f-irreducible** (Def. after `BasicIrreducible`): `G`
is *f-reducible to* a nonempty induced subgraph `H` iff `H` is `f_H`-choosable;
`G` is *f-irreducible* if it reduces to no such `H`. This — not edge-deletion
list-criticality — is what the discharging / edge-lower-bound program uses.

Our current `EdgeFCritical` / `KListCritical` (Lean) and `bk.is_choice_critical`
(Python) are the *classical* edge-deletion list-critical notion. That notion is
real and appears in Cranston–Rabern's edge-bound papers, so keep it — but add
**f-irreducible as the primary notion**, since it is the one the book (and the BK
attack) is built on. Flag both clearly so we never conflate them.

## Theorem corpus → `Literature` (statements-first, in dependency order)

Each becomes a `Literature/Coloring/<Label>/` entry (Statements.lean typechecks;
Proofs.lean may be `sorry`; status.toml keyed to the book's label). Suggested
order (cheap/foundational first):

1. `FirstListBound` — `|L(v)| > d(v) ⇒ L-colorable` (greedy; we already have the
   analogous `choosable_card`).
2. `BasicIrreducible` — f-irreducible ⇒ `f(v) ≤ d(v)`, hence `2|E| ≥ f(V)`. The
   seed of every edge lower bound; small once f-irreducible is defined.
3. `SecondListBound` — acyclic orientation, `|L(v)| > d⁺(v) ⇒ L-colorable`.
4. `KernelPerfectListBound` / `KernelPerfectSuperListBound` /
   `KostochkaYanceyKernelLemma` — the kernel-perfect generalization.
5. Combinatorial Nullstellensatz lemma; the Eulerian-orientations lemma
   (`p_k(G) = |EE|−|EO|`); the Schauz coefficient formula. **These are the formal
   statements the empirical `alon_tarsi` certificates correspond to** — proving
   them makes an AT certificate a witness of a formalized theorem, not just a
   solver assertion.
6. Brooks' theorem and its list-coloring form (Kernel magic chapter).
7. Edge coloring (`DeltaEdgeColoring`), toward the BK-for-line-graphs setting.

## Two source documents (both Rabern, same project)

| Source | What it is | Role |
|---|---|---|
| `basic graph coloring.tex` | Fuller, 9-chapter book (1402 lines) | **Primary spine** — definitions, list-coloring, irreducibility, kernel magic, nullstellensatz. Uniquely has `BasicIrreducible`, the Kernel-Magic + Nullstellensatz chapters, Hall/Menger/Haxell transversals |
| `gct.tex` ("graph coloring tools") | Shorter, flat (702 lines) | Mostly a subset, but **uniquely carries the BK-endgame clique-structure theory** (below) + explicit max-flow/min-cut (Menger) for the transversal proofs |

Same theorems/labels/development throughout; treat `basic` as the foundational
reference and mine `gct` for the endgame lemmas.

## BK-endgame corpus (from `gct.tex`) — advanced, downstream

The "χ = Δ ⇒ big cliques" structure theory nearest the north star. **Depends on
clique / `ω` / `Δ` / max-clique-collection machinery not yet defined** (define
those before attempting these). Literature statement-entries, in order:

1. `HajnalLemma` — for maximum cliques `𝒬`: `|⋃𝒬| + |⋂𝒬| ≥ 2ω(G)`. The base
   counting lemma; needs only cliques + `ω`.
2. `KostochkaCliqueGraph` — if `ω(G) > ⅔(Δ+1)` and the clique-graph `X_𝒬` is
   connected, then `⋂𝒬 ≠ ∅`. (Needs the clique-intersection graph `X_𝒬`.)
3. `TwoThirdsEqualityStructure` — the `ω(G) ≥ ⅔(Δ+1)` boundary case: either
   `⋂𝒬 ≠ ∅`, or `Δ(X_𝒬) ≤ 2` with a rigid half-`ω` intersection pattern.
4. `transitiveClustering` (observation) + `TransitiveClusteringBigCliques` — for
   connected vertex-transitive `G` with `ω ≥ ⅔(Δ+1)`: `X_𝒬` is edgeless, or a
   cycle with each vertex blown up to `K_{ω/2}`.

These sit downstream of the foundations (they need `ω`, `Δ`, the max-clique
collection, and the clique-intersection graph `X_𝒬`), so they are a later tier of
Literature entries — but they are the ones closest to the actual Borodin–Kostochka
attack, so worth stating early even while proofs stay `sorry`.

## Ties to the empirical tier

- `polynomials.py` / `alon_tarsi.py` compute exactly the book's `p_k(G)` and the
  Eulerian even/odd count — the nullstellensatz chapter is their spec. Proving
  the Eulerian-orientations lemma in Lean would let an AT certificate be checked
  against a formalized statement (a genuine formal↔empirical bridge instance).
- `bk.py` bad-K2 / criticality: reconcile its `is_choice_critical` naming with
  the book (edge-deletion vs f-irreducible) per the correction above.

## Next Lean increment (once `Basic.lean` is green)

1. `GNumbering` (safe), then `SimpleGraph.induce`-based `f_H`, then
   `FReducible` / `FIrreducible`.
2. First two Literature entries: `FirstListBound`, `BasicIrreducible`.
3. Reframe PLAN §6 ("what mathlib provides / what must be built") to key off this
   book's development rather than a generic list.

## Source
`landon.github.io/notes/BasicGraphColoring.pdf` (uploaded `basic graph coloring.tex`).
Chapters: Graphs; Coloring vertices (Brooks, list coloring, prescribed list
sizes); List coloring complete graphs; Kernel magic; Combinatorial
nullstellensatz; Independent transversals; Vertex partitions; Coloring edges.
