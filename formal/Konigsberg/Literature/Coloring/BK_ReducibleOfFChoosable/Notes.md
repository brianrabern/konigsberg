# BK_ReducibleOfFChoosable

## Informal statement
If `G` is `D`-critical (`KCritical G D`), `s` is a nonempty core, `dG` upper-bounds the
ambient degree (`∀ v, G.degree v ≤ dG v`), and the induced core `G.induce s` is
`FChoosableZ` for the reducibility demand `f(w) = (D−1) − (d_G(w) − deg_{G[s]}(w))`, then
`False` — no such `G` exists, so the configuration is forbidden in any minimal BK
counterexample (under H_BK).

`KCritical` here is the **hereditary** form (`¬ Colorable (k−1)` and every proper
`Subgraph H ≠ ⊤` is `(k−1)`-colorable), not textbook vertex-criticality.
`FChoosableZ (↑ ∘ g)` is the same as `FChoosable g` (`fChoosableZ_coe`); `Colorable k`
is the same as `ListColorable` of constant `range k` lists
(`colorable_iff_listColorable_const`). Demand is ℤ-valued so `D−1` is not ℕ-truncated
at `D = 0`. Non-vacuity: `CompleteGraphKCritical.completeGraph_kCritical`.

### Statement provenance (fidelity)
The proved constant differs from the original agent-drafted signature; source has been
reconciled to what was proved in-env. Choices, all load-bearing:
- **Minimal-counterexample form (`⇒ False`).** Criticality is a hypothesis and the
  conclusion is `False`, so the lemma is the forbidden-configuration statement directly.
  The positive "rest-colorable ⇒ `Colorable (D−1)`" form is an internal step.
- **ℤ-valued inline demand (`FChoosableZ`), not a bespoke ℕ `reducibilitySlack`.**
  Avoids ℕ truncation at `D = 0`, which would silently misstate the demand. The ℕ slack
  def was removed; do not reintroduce it.
- **`dG` generalized with a lower bound**, not `= G.degree`. `FChoosableZ` is antitone in
  the demand (`fChoosableZ_mono`), so this is strictly stronger and specializes to
  `dG := G.degree` by `le_refl`. `s.Nonempty` is required (makes `sᶜ` a proper subgraph).
- **`hchi : χ(G) = D` dropped** — the contradiction lives in `KCritical`, not a separate
  chromatic hypothesis.

### Status / open gaps
- **Formalized in source** (`Proofs.lean`): rest-list cardinality, glue, and the
  `KCritical → False` wrapper. `#print axioms` is the whitelist
  `{propext, Classical.choice, Quot.sound}`. Transport lemmas
  (`deleteVerts_ne_top`, `exists_rest_coloring`, `fChoosableZ_mono`) are local to
  this entry — they were never in `Areas/` and are not imported from a session-only
  `BKBridge` namespace.
- **Non-vacuity witnessed.** A `⇒ False` lemma is worthless if `KCritical G D` is
  unsatisfiable. The witness is `CompleteGraphKCritical.completeGraph_kCritical`
  (`K_k` is `k`-critical for `k ≥ 1`, formalized), and [`SanityChecks.lean`](SanityChecks.lean)
  instantiates it at K₃.

Proof decomposition: see `docs/handoff/BK_REDUCIBLE_BRIDGE_PROOF.md`.

## Source
Konigsberg reducibility bridge (`BK.reducible_of_fChoosable`).

## Provenance
Agent-drafted stated target for the reducible-configuration engine; human fidelity read;
proved in-tree.

## Fidelity review
The empirical tool tests `f`-choosability (over-approximation of the constrained
adversary). This lemma is the mathematical bridge from a HIT to “forbidden
configuration.” Because the entry is `formalized`, `reducible_configuration` HITs
drop `[conditional on reducibility bridge lemma BK.reducible_of_fChoosable]`
(fail-closed on Literature status). Claims still name H_BK.

`KCritical` = hereditary subgraph-criticality (same as the `Areas.Coloring` def; not
vertex-criticality alone). `FChoosableZ` is the same as list-choosability over ℕ,
written in ℤ.

## Sanity checks
Vacuous `f`-choosability on the empty graph, and the K₃ `KCritical` instance, live in
[`SanityChecks.lean`](SanityChecks.lean) (`example` only; independent of the bridge
proof). See `docs/TRUST.md`.

## Referee report

```
Recommendation: accept
Review mode: full adversarial + heuristic
Established:
  - bespoke definitions ['DecidableEq', 'DecidablePred', 'DecidableRel', 'FChoosableZ', 'KCritical'] present — names only; no unmatched standard-notion claim (meaning is for the adversarial pass)
  - tested hypotheses ['Nonempty'] — no counterexample found by heuristics
  - no vacuity/triviality heuristic fired
  - no scope-creep heuristic fired
  - literature_search('Konigsberg Literature Coloring ReducibleOfFChoosable reducible fChoosable') → 4 hit(s); true≠new — calibrate novelty
  - The theorem type-checks and #print axioms shows only [propext, Classical.choice, Quot.sound] — a clean kernel-valid proof (lean_check).
  - KCritical unfolds to ¬G.Colorable(D−1) ∧ (∀ proper subgraph H≠⊤, H.coe.Colorable(D−1)) — a genuine criticality predicate (lean_check #print).
  - FChoosableZ unfolds to the standard list-colorability quantifier over ListAssignment with |L(v)| ≥ f(v) — faithful to f-choosability (lean_check #print).
  - The proof body is a genuine reducibility argument: color G−s by criticality (exists_rest_coloring), transfer to residual lists on G[s] (fChoosableZ_mono), extend via colorable_of_rest_and_fChoosable to G.Colorable(D−1), contradicting hcrit.left.
  - Non-vacuity: completeGraph_kCritical provides real KCritical witnesses (K_k is k-critical), so the hypothesis is inhabited.
  - The f-function (D−1)−(dG(w)−deg_{G[s]}(w)) with external degree bound dG is a faithful (slightly generalized, monotone) form of the residual-list-size in the standard BK reducibility bridge.
Minor issues:
  - The bridge is stated purely as an implication to False (reducibility as a contradiction). Its usefulness depends on the downstream discharging closure (BK_DischargingClosure, currently status 'stated', not proved) — this artifact is a lemma, not the BK theorem itself; the citation/docstring should keep that scope explicit.
  - Novelty is calibrated: this is the documented reducibility bridge already present in Literature as 'formalized'; promotion is a status upgrade of a known construction, not a new mathematical result.
Suggested revision:
  Promote as-is. Recommend the Literature note explicitly record: (i) reducibility is encoded as 'FChoosableZ(G[s], residual) → False under D-criticality', i.e. a contradiction lemma to be combined with unavoidability; (ii) the dG parameter is an external upper degree bound generalizing actual G-degree via fChoosableZ_mono; (iii) non-vacuity witness completeGraph_kCritical.
Checks:
  - (definition_predicate_faithfulness) pass: bespoke definitions ['DecidableEq', 'DecidablePred', 'DecidableRel', 'FChoosableZ', 'KCritical'] present — names only; no unmatched standard-notion claim (meaning is for the adversarial pass)
  - (empirical_cross_check) na (na: property not matched to independent_hitting_set or other tools): no registered empirical tool maps to this claim's predicate
  - (hypothesis_necessity) pass: tested hypotheses ['Nonempty'] — no counterexample found by heuristics
  - (vacuity_triviality) pass: no vacuity/triviality heuristic fired
  - (scope_creep) pass: no scope-creep heuristic fired
  - (significance_novelty) pass [literature_search]: literature_search('Konigsberg Literature Coloring ReducibleOfFChoosable reducible fChoosable') → 4 hit(s); true≠new — calibrate novelty
  - (definition_predicate_faithfulness) pass [lean_check]: KCritical and FChoosableZ unfolded via #print; both match standard k-criticality and f-choosability. f = (D−1)−(dG−deg_{G[s]}) is the standard residual list size.
  - (kernel_axioms) pass [lean_check]: #print axioms = [propext, Classical.choice, Quot.sound]; no sorry/extra axioms.
  - (proof_meaning_gap) pass [lean_check]: Proof term genuinely composes rest-coloring + monotonicity + extension into hcrit.left contradiction; predicate matches intended reducibility bridge.
  - (vacuity_triviality) pass [lean_check]: completeGraph_kCritical supplies real KCritical instances; hypothesis non-vacuous.
  - (empirical_cross_check) na [reducible_configuration] (na: The claim is a universal Lean implication over abstract V and abstract KCritical/FChoosableZ; no single graph6 instance discriminates its truth. Empirical tools test specific configurations, not the meta-bridge.): 
  - (hypothesis_necessity) pass [lean_check]: s.Nonempty is load-bearing (deleteVerts_ne_top requires it); KCritical supplies both the non-colorability (final contradiction) and the rest-colorability; degree bound feeds the list sizes.
  - (significance_novelty) minor [literature_search]: Documented BK reducibility bridge already 'formalized' in Literature; downstream closure lemma is only 'stated'. Correct but a known construction.
```
