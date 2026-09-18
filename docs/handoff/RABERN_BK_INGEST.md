# Standing on Rabern's shoulders — BK corpus gap analysis + ingestion (Cursor spec)

*Goal: when Hunt mode runs, it should start from Rabern's actual method and known
results, not rediscover them. This audits the corpus against Rabern's body of work and
recent BK progress, and prioritizes what to ingest. The organizing judgment: encode
**method and reusable structural theorems**, plus Rabern's **specific forbidden
configurations** as hunt seeds — and deliberately **do not** bulk-ingest the
forbidden-subgraph-class zoo (those are endpoints, not tools).*

Statements-first, per `STATEMENTS_FIRST_INGEST.md` and `FIDELITY_GATES.md`: each entry
ships an informal statement, a `stated` Lean signature that typechecks, and SanityChecks;
proofs come later. Ingest none of this as `formalized`.

---

## What's already in (good coverage — do not re-add)

Rabern's *Basic Graph Coloring* machinery and his core BK papers are present:
`BasicIrreducible` (formalized), `RabernBook_FirstListBound`/`SecondListBound`
(formalized), `BrooksListForm`, `CombinatorialNullstellensatz`, `KernelPerfectListBound`
/`KernelPerfectSuperListBound`, `KostochkaYanceyKernelLemma`, `SchauzCoefficient`,
`EulerianOrientationsLemma`, `HajnalLemma`, `KostochkaCliqueGraph`,
`TransitiveClusteringBigCliques`, `TwoThirdsEqualityStructure`, plus the BK papers
`CranstonRabern_BKEquivalentConjectures` (1203.5380), `CranstonRabern_BrooksAndBeyond`
(1403.0479), `CranstonRabern_ChiEqDeltaBigCliques` (1305.3526),
`CranstonRabern_ImprovedEdgeBound` (1602.02589), `KiersteadRabern_OreVizing` (1406.7355),
`Rabern_4ListCriticalEdgeBound`, `Rabern_HittingMaxCliques` (0907.3705). The
degree-choosability / Gallai-tree engine is in `Areas/Coloring/Gallai.lean`, and the
reducibility bridge in `BK_ReducibleOfFChoosable`. This is Rabern's engine — the
`f(v) = d(v)−1` f-choosable-join method — largely already encoded.

**So the point of this pass is not breadth. It's the few high-leverage gaps below.**

---

## Tier 1 — Highest value: seed the engine with Rabern's KNOWN forbidden configurations

This is what "standing on his shoulders" concretely means. Rabern's BK method proves
specific small **joins are `f`-choosable with `f(v)=d(v)−1`**, hence cannot be induced
subgraphs of a vertex-critical χ=Δ graph — i.e. they are *forbidden configurations*. The
hunt currently rediscovers C₄/C₆ from zero. Instead, pre-load his catalogue as seed cores
for `reducible_configuration` / the campaign staircase.

Action: extract the reducible joins from **Cranston–Rabern, "Coloring a graph with Δ−1
colors"** (the minimum-counterexample study behind 1203.5380) and **"Coloring claw-free
graphs with Δ−1 colors"** (Tier 2) and encode each as:
- a `make_graph` recipe (graph6 + degree spec) in a seed list the campaign can enumerate;
- optionally a `stated` Lean lemma "this join is `f`-choosable for `f=d−1`".

This turns the staircase's rung 2 ("mint a new forbidden core") from blind search into
"work through Rabern's list, then extend past it." Put the seed list where `campaign.py`
can read it (a `reducible_seeds.toml` or a module constant), and have the staircase cite
the next *unencoded* Rabern config before inventing new ones.

## Tier 2 — Rabern's BK structural theorems not yet in corpus

1. **Cranston–Rabern, claw-free BK.** "Coloring claw-free graphs with Δ−1 colors," SIAM
   J. Discrete Math. 27 (2013) 534–549. Every claw-free graph with χ ≥ Δ ≥ 9 contains
   `K_Δ`. Flagship Rabern BK theorem; its proof *is* the join/reducibility engine at
   work. `stated` entry `CranstonRabern_ClawFreeBK`, area coloring.
2. **Cranston–Lafayette–Rabern, (P₅,gem)-free BK.** "Coloring (P₅,gem)-free graphs with
   Δ−1 colors," J. Graph Theory 101 (2022) 633–642. `stated` entry
   `CranstonLafayetteRabern_P5GemFreeBK`.

Both are Rabern-authored, method-consistent, and give the hunt worked reductions to
imitate rather than class-specific tricks.

## Tier 3 — Foundational "what's known" frame (context the hunt must have)

3. **Reed's large-Δ BK.** BK holds for Δ ≥ a large constant (Reed, 1999,
   *ω, Δ, and χ*). The live regime is small Δ (=9). Add at least a `literature`
   `REFERENCES.toml` entry; ideally a `stated` `Reed_BKLargeDelta` so the hunt knows the
   general conjecture is already settled for large Δ and does not waste circuits there.
4. **Constructive large-Δ (new).** "On the Borodin–Kostochka conjecture for graphs with
   large maximum degree," arXiv:2603.16670 — χ ≤ Δ for ω < Δ and Δ ≥ 5.2×10⁹, a
   *constructive* reorganization of Reed's framework (minimal-counterexample structure +
   probabilistic coloring made constructive). `REFERENCES.toml` entry; the constructive
   reorganization is the methodologically interesting part.

## Tier 4 — Genuinely new *methods* worth a stated entry (not endpoints)

5. **Vertex partitions relative to a maximum clique.** "Progress on the Borodin–Kostochka
   conjecture: a structural approach via vertex partitions relative to a maximum clique,"
   AIMS Math. (2026), doi:10.3934/math.2026349. Gives a *sufficient condition* for
   χ ≤ Δ−1 by partitioning vertices on their neighbor-count in a fixed max clique — a
   reusable lens, not a single class. `stated` entry `VertexPartitionRelMaxClique_BK`.
6. **Correspondence (DP) coloring BK.** arXiv:2603.14427 (Eurocomb'25). Relevant because
   the harness already has choosability/DP machinery; the correspondence generalization
   may transfer. `REFERENCES.toml`, or `stated` if the statement is clean.
7. **BK ↔ partition into clique-bounded classes.** arXiv:2311.08772. `REFERENCES.toml`.

## Tier 5 — Do NOT bulk-ingest (explicit recommendation)

The recent literature is dominated by "BK for (forbidden-subgraph-class) graphs":
odd-hole-free (2310.07214), P₆-free (2306.12062), (P₇,C₄)-free, (P₅,C₄)-free, {4K₁}-free
(1801.01310), K̄₁,ₜ-free, (P₇,C₄,bull/kite)-free, etc. These are **endpoints, not tools**:
each uses ad-hoc structure specific to its excluded subgraph and yields no reusable
machinery for the general conjecture. Ingesting them would bloat the corpus and steer the
hunt toward class-specific dead-ends — the mission already (correctly) treats "prove BK
for restricted class X" as *not* the goal. Cite at most one or two in `REFERENCES.toml`
for completeness; do not create `stated` entries or seed the hunt with them.

---

## Two mission/engine notes (beyond ingestion)

- **The staircase needs a discharging rung.** Rabern's method is reducibility **+**
  discharging/unavoidability; the corpus and the staircase encode the reducibility half
  only. Seeding forbidden configs (Tier 1) raises the value of the reducibility half but
  does not add the discharging half — accumulating forbidden cores still never composes
  into a proof without it. Flag as the next real design gap (out of scope for this ingest).
- **Point the hunt at Rabern's catalogue first.** Once Tier 1 lands, update `MISSION_BK`
  / the staircase to say: exhaust Rabern's known forbidden joins and his claw-free /
  (P₅,gem)-free reductions before inventing configurations, and treat class-restricted BK
  results as reference, not as targets.

## Acceptance

- Tier 1 seed list encoded and readable by `campaign.py`; staircase cites the next
  un-encoded Rabern config before blind search.
- `stated` entries (typecheck + SanityChecks) for claw-free BK and (P₅,gem)-free BK;
  Reed large-Δ at least as a reference, ideally stated.
- `REFERENCES.toml` updated: constructive large-Δ (2603.16670), vertex-partition method
  (2026), correspondence BK (2603.14427); at most 1–2 class-specific papers.
- No new `formalized` claims from this pass; no bulk class-zoo ingestion.

Sources for citations are listed in the chat message accompanying this handoff.
