# Investigation state — hitting all maximum cliques with an independent set (Rabern)

Recovered research notes for the Rabern hitting-set problem, so a session can be
resumed after a crash. Clearly separates **certified** facts (tool-backed this
session), **literature** statements (cited, not verified here), and
**interpretation/conjecture** (proof-pending). Do not upgrade across these lines.

## The problem

When does a graph G have an independent set I meeting **every maximum clique**?
Equivalently (Rabern's phrasing): an independent set I with ω(G−I) < ω(G).
Tool: `independent_hitting_set(graph6)` — decides it, re-checks the witness.

## Literature (cited, not verified here — now in REFERENCES.toml)

- **Rabern's theorem** (arXiv:0907.3705; also `stated` Lean entry
  `Rabern_HittingMaxCliques`): if **ω(G) ≥ ¾(Δ(G)+1)** then G has an
  independent set meeting every maximum clique. **The threshold constant is ¾, NOT
  ⅔.** (The ⅔ bound is the *separate* clique-intersection result
  `TwoThirdsEqualityStructure` — do not conflate them; we did, and it was wrong.)
- **King** (arXiv:0911.1741) improved Rabern's ¾ via lopsided independent
  transversals. The **sharp constant is open** ("hitting every large maximal clique
  with a stable set", Open Problem Garden).

## Certified this session (tool-backed, independently re-verified)

- The unconditional property is **false**; the **smallest counterexample is C₅**
  (n=5, ω=2). Structural reason: for triangle-free graphs the maximum cliques are
  the edges, so the property ⟺ "independent vertex cover exists" ⟺ **bipartite**;
  the smallest non-bipartite triangle-free graph is C₅.
- **Census, connected graphs, δ≥2** (degree-≤1 vertices are free to add to any
  hitting set, so they don't affect feasibility — a valid reduction):
  - n≤5: only C₅ fails.
  - n=6: exactly **one** failure (`EheO`, ω=2, Δ=3).
  - n=7: **9 failures** — 8 with ω=2 and **one with ω=3** (`FzM]W`, Δ=4). This
    ω=3 case **refutes** the tentative "all failures are ω=2 / C₅-like" pattern
    (it held through n≤6 and broke at n=7 — a small-case artifact).
  - **Every** failure up to n=7 satisfies **ω < ¾(Δ+1)** — 0 violations of
    Rabern's theorem across all 995 connected graphs n≤7 (empirical confirmation
    of the ¾ bound on small graphs).
- **The C₅[Kᵣ] clique-blow-up family fails for all r checked** (r=1,2,3): it has
  ω=2r, Δ=3r−1, so **ω/(Δ+1) = 2/3 exactly** for every r — an infinite failing
  family pinned at ratio 2/3. The independent blow-up C₅[K̄₂] and the Mycielskian
  μ(C₅) = Grötzsch (ω=2) also fail.
- **Edge-fragility of the boundary example:** C₅[K₂] fails, and **all 25 single
  edge deletions flip it to holding** — it is maximally fragile / edge-minimally
  failing.

## The corrected picture (this is the interesting frame)

Rabern *proves* holding at ω/(Δ+1) ≥ **3/4**; our failing family lives at
ω/(Δ+1) = **2/3**. So the truth sits in the **open band [2/3, 3/4]**, and the whole
question is: **what is the sharp constant c with "ω ≥ c(Δ+1) ⟹ hitting set"?**
Everything below is a way to attack that.

## Open threads to pursue next

1. **Probe the [2/3, 3/4] band.** Search for failures with 2/3 < ω/(Δ+1) < 3/4
   (odd-cycle / clique blow-ups tuned to land in the band). Whether such failures
   exist tells you how far Rabern's ¾ can be pushed down — and whether 2/3 is the
   real threshold. (Honest: a sweep can *refute* "no failures above 2/3", never
   *confirm* a universal.)
2. **Characterize the failing family.** Is every failure an "odd cycle of cliques"?
   The right invariant is the **maximum-clique intersection hypergraph** and when it
   admits an independent transversal — an "odd-hole among the maximum cliques"
   characterization. **Missing tool:** one that extracts/manipulates that hypergraph
   directly. `FzM]W` (the ω=3, n=7 failure) is the first non-blow-up failure —
   characterize it.
3. **Census the edge-minimally-failing graphs** (every overlap-edge deletion
   restores hitting; C₅[K₂] is one). These "minimal cores" are the bridge from the
   empirical families to a theorem.
4. **Two proof targets** (would let the findings stand on their own, not lean on the
   stated ⅔/¾ results):
   - **Lemma A (blow-up ratio):** ω/(Δ+1) is invariant under the clique blow-up Bᵣ.
     General, elementary, no dependence on any threshold theorem.
   - **Lemma B (reduction):** for triangle-free G, hitting ⟺ independent edge cover
     ⟺ bipartite — proving the C₅-based failure family.
   First check with `lean_check` whether the clique/degree/blow-up primitives are in
   scope before promising a Lean proof.

## Honesty boundary (carry these hedges)

- Certified: the (Δ,ω) coordinates, the fail/hold verdicts, and arithmetic like
  "ω/(Δ+1)=2/3 for C₅[Kᵣ]".
- Literature (cited, not verified here): Rabern's ¾ theorem, King's improvement.
- Interpretation / conjecture (proof-pending): that any constant is *the sharp*
  threshold, that the C₅ family is *extremal*, and any universal ("all r fail",
  "no failures above 2/3").

## Referee review + correction (blow-up reduction)

A later session proved a Lean theorem (`RabernBlowupV2.main`) and narrated it as
"H[Kᵣ] hits its maximum cliques ⟺ H bipartite, for all H." **Referee verdict:
major revision.** The proof is kernel-valid, but its left-hand predicate is
*cross-blob-edge hitting*, which equals the real maximum-clique hitting property
**only for triangle-free H**. Decisive tool-grounded check (real property via
`independent_hitting_set` vs. the claimed "⟺ H bipartite"):

| base H | triangle-free | H bipartite | hits(H[K₂]) *real* | claim agrees |
|---|---|---|---|---|
| K₃ | no | no | **holds** | **NO** |
| K₄ | no | no | **holds** | **NO** |
| diamond | no | no | **holds** | **NO** |
| bull | no | no | **holds** | **NO** |
| C₅ | yes | no | fails | yes |
| C₆ | yes | yes | holds | yes |

So the unqualified claim is **false on every triangle-ful base** (a triangle merges
three blobs into one big clique, so the max cliques are no longer the edge-cliques).
The `main` theorem is a true lemma about a *proxy* predicate; it is not the hitting
property.

**Corrected statement (the actual deliverable):**
> For **triangle-free** H and r ≥ 1: H[Kᵣ] admits an independent set meeting every
> **maximum clique** ⟺ H is bipartite. (r = 1 is the proved ω=2 theorem.)

**Formal status, honestly:**
- **Kernel-proved:** ω=2 ⟺ bipartite (edge-transversal core); the cross-blob-edge
  reduction lemma. Both clean-axiom.
- **Stated, NOT yet proved over the real predicate:** the corrected triangle-free
  statement above — proving it needs the step tying "meets every maximum clique" to
  "meets every cross-blob edge" *under triangle-freeness*, which `main` does not do.

**Required load-bearing sanity check** (for the in-tree entry): instantiate at K₃ —
`independent_hitting_set(K₃[K₂]) = holds` while K₃ is non-bipartite — so the theorem
is **false without the triangle-free hypothesis**. That check makes the hypothesis
provably necessary, not decorative.

**To do (Cursor, in-tree):** create `Literature/Coloring/HittingCliqueBlowup/` with
(a) `Statements.lean` stating the corrected triangle-free theorem over the *maximum
clique* hitting predicate (proof `sorry`), (b) `SanityChecks.lean` with the K₃
hypothesis-necessity check + a non-vacuity witness, (c) `Notes.md` carrying this
referee report and citing the proved ω=2 core it rests on. Do **not** promote `main`
as "the hitting reduction" — it is the cross-edge proxy lemma, and should be filed as
such if kept.

## Tools available for this

`independent_hitting_set`, `make_graph`, `mycielskian`, `blow_up`, `clique_number`,
`independence_number`, `enumerate_graphs`, plus `literature_search` (now returns
Rabern's exact ¾ statement from REFERENCES.toml).
