# CompleteGraphKCritical

## Informal statement
For every `k ≥ 1`, the complete graph `K_k` is `k`-critical in the **hereditary**
sense of `Areas.Coloring.KCritical`: it is not `(k−1)`-colorable, **and every
proper `SimpleGraph.Subgraph` `H ≠ ⊤` has `H.coe` `(k−1)`-colorable**. That
quantifier runs over all proper subgraphs (vertex-deleted and spanning
edge-deleted), so it subsumes both the vertex-critical and edge-critical
readings. Folklore; this entry is the non-vacuity witness that `KCritical` is
satisfiable.

## Source
Folklore (K_k is the canonical k-critical graph).

## Provenance
Agent-drafted stated target; statement written against `Areas.Coloring.Basic.KCritical`.
Proved in `Proofs.lean`; status `formalized`.

## Role (why this entry exists)
Non-vacuity witness for the two BK bridges, both of which conclude `KCritical G D → … →
False`. A `⇒ False` lemma is vacuous — and worthless — if `KCritical` is unsatisfiable.
`K_k` shows it is inhabited for all `k ≥ 1`, so the reducibility bridge
([[BK_ReducibleOfFChoosable]]) and the discharging closure ([[BK_DischargingClosure]])
are non-vacuous. The referee's `⇒ False`-vacuity check should point at this witness.
This is a folklore infrastructure lemma, not a new theorem.

## Fidelity review
`KCritical G k` is **not** textbook vertex-criticality alone. It is
`¬ Colorable (k−1) ∧ ∀ H : G.Subgraph, H ≠ ⊤ → H.coe.Colorable (k−1)` — hereditary
over the full subgraph lattice. For `K_k` that is the intended statement (and is
true): omitting a vertex yields at most `K_{k−1}`; omitting an edge lets the two
endpoints share a colour.

The first conjunct is χ(K_k) = k, via `Colorable.card_le_of_pairwise_adj`. The
second is the case split above (`Fintype.card_subtype_lt` then `colorable_of_fintype`,
or identify the non-adjacent endpoints). Do not weaken `hk : 1 ≤ k` away (K_0 is
degenerate). Spelling is `KCritical (completeGraph (Fin k)) k` because `KCritical`
is not a `SimpleGraph` projection.

## Sanity checks
Independent probes in [`SanityChecks.lean`](SanityChecks.lean): K₃ is not
2-colorable, and K₃ is 3-colorable (`colorable_of_fintype`). See `docs/TRUST.md`.

## Referee report

```
Recommendation: accept
Review mode: full adversarial + heuristic
Established:
  - bespoke definitions ['CompleteGraphKCritical', 'KCritical'] present — names only; no unmatched standard-notion claim (meaning is for the adversarial pass)
  - no vacuity/triviality heuristic fired
  - no scope-creep heuristic fired
  - literature_search('Konigsberg Literature Coloring CompleteGraphKCritical completeGraph kCritical') → 4 hit(s); true≠new — calibrate novelty
  - The theorem statement elaborates as `∀ (k : ℕ), 1 ≤ k → KCritical (completeGraph (Fin k)) k`, verified via #check.
  - KCritical unfolds to `¬G.Colorable (k-1) ∧ ∀ (H : G.Subgraph), H ≠ ⊤ → H.coe.Colorable (k-1)` (standard subgraph-hereditary criticality), confirmed via #print.
  - Proof depends only on [propext, Classical.choice, Quot.sound] — clean, no sorry/extra axioms (#print axioms).
  - Semantic content matches complete-graph facts: independent tool check gives χ(K_5)=5, ω=5, i.e. K_k is not (k-1)-colorable, consistent with the first conjunct.
  - Non-vacuity witnessed: `KCritical (completeGraph (Fin 2)) 2` and `KCritical (completeGraph (Fin 3)) 3` both elaborate from the theorem.
  - Hypothesis `1 ≤ k` is load-bearing: for k=0, k-1=0 in ℕ and the empty graph is 0-colorable (proved), so the first conjunct ¬Colorable(0) fails and KCritical would be false without the hypothesis.
  - Citation docstring explicitly flags the subgraph-hereditary vs vertex-critical distinction, closing the main meaning gap.
  - Component lemmas type-check with intended statements: completeGraph_not_colorable_pred (¬Colorable (k-1)) and completeGraph_proper_subgraph_colorable (proper subgraphs are (k-1)-colorable).
Minor issues:
  - The bespoke predicate `KCritical` uses subgraph-hereditary criticality (`∀ proper Subgraph H, H is (k-1)-colorable`), which is stronger/different from the more common vertex-critical notion (deleting any single vertex lowers χ). The docstring already discloses this, so it is non-blocking, but promoted Notes should retain that disclaimer verbatim so downstream users do not misread it as vertex-criticality.
  - Result is explicitly folklore (χ(K_k)=k and hereditary criticality); novelty is nil, but it is registered honestly as a non-vacuity witness for the BK bridges, which is a legitimate library role.
Suggested revision:
  Promote as-is. Ensure the Literature Notes preserve the citation's explicit 'hereditary/subgraph sense, not vertex-critical' caveat so the KCritical predicate is not misread as standard vertex-criticality.
Checks:
  - (definition_predicate_faithfulness) pass: bespoke definitions ['CompleteGraphKCritical', 'KCritical'] present — names only; no unmatched standard-notion claim (meaning is for the adversarial pass)
  - (empirical_cross_check) na (na: property not matched to independent_hitting_set or other tools): no registered empirical tool maps to this claim's predicate
  - (hypothesis_necessity) na (na: claim has no parseable conditional hypotheses): no identifiable hypotheses to test
  - (vacuity_triviality) pass: no vacuity/triviality heuristic fired
  - (scope_creep) pass: no scope-creep heuristic fired
  - (significance_novelty) pass [literature_search]: literature_search('Konigsberg Literature Coloring CompleteGraphKCritical completeGraph kCritical') → 4 hit(s); true≠new — calibrate novelty
  - (definition_predicate_faithfulness) pass [lean_check (#print KCritical)]: KCritical = ¬Colorable(k-1) ∧ (∀ proper Subgraph H, H.coe Colorable (k-1)); a legitimate subgraph-hereditary criticality notion, and the citation explicitly distinguishes it from vertex-criticality.
  - (empirical_cross_check) pass [chromatic_number, clique_number]: χ(K_5)=5 and ω=5 via tools, consistent with the theorem's 'not (k-1)-colorable' conjunct for a discriminating instance.
  - (hypothesis_necessity) pass [lean_check]: Stripping 1 ≤ k breaks k=0: empty graph is 0-colorable (proved), so ¬Colorable(0-1)=¬Colorable(0) is false. Hypothesis is load-bearing.
  - (vacuity_triviality) pass [lean_check]: Non-vacuous: KCritical for K_2 and K_3 elaborate directly from the theorem.
  - (axiom_cleanliness) pass [lean_check (#print axioms)]: Depends only on propext, Classical.choice, Quot.sound; no sorry/custom axioms.
  - (significance_novelty) minor [literature_search]: Folklore result, no novelty, but registered honestly as a non-vacuity witness for BK bridges.
```
