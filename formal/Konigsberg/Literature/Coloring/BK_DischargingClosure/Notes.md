# BK_DischargingClosure

## Informal statement
If every configuration in a finite set 𝒞 is reducible (absent from any D-critical
K_D-free graph — from `reducible_of_fChoosable`) and 𝒞 is unavoidable (every
D-critical K_D-free graph contains some C ∈ 𝒞), then there is no D-critical
K_D-free graph. Hence every graph with Δ = D and ω < D is (D−1)-colorable —
Borodin–Kostochka at D.

`reducible_and_unavoidable_imp_no_counterexample` is the discharging counterpart
of `BK.reducible_of_fChoosable`. Instantiated at a graph `G`, `Contains`
abstracts “G contains some member of 𝒞”: reducibility gives `¬ Contains` on any
D-critical K_D-free G, unavoidability gives `Contains`, and the composition is
`False`.

`borodinKostochka_at_nine` is the live-regime slice: Δ = 9 implies
(max{8, ω})-colorable. Its type is not definitionally the general conjecture
`9 ≤ Δ → Colorable (max (Δ−1) ω)`. A kernel proof of the slice is a Δ=9
milestone; it must not settle the general campaign.

### Status / open gaps
- Stated. Both theorems are `sorry`. The empirical `discharging_unavoidable`
  tool can mint an UNAVOIDABLE Claim only as enumeration-checked and
  **conditional** on this closure until it is kernel-proved.
- Joint inhabitation of `KCritical G 9 ∧ G.cliqueNum < 9` is exactly a minimal
  BK counterexample at Δ=9 (unknown). SanityChecks witness the conjuncts
  *separately*: the empty graph is not 9-critical; K₉ is not K₉-free.

## Source
Konigsberg discharging closure (`BK.reducible_and_unavoidable_imp_no_counterexample`);
Borodin–Kostochka at the Δ=9 crux. See `docs/handoff/FULL_METHOD_DISCHARGING.md` Part C.

## Provenance
Agent-drafted stated target for the discharging engine; human fidelity read of
the method spec (reducible + unavoidable ⇒ no counterexample).

## Fidelity review
The empirical tool verifies a proposed (μ, rules, 𝒞) argument at D=9 and, on a
HIT, mints that 𝒞 is UNAVOIDABLE in 9-critical K₉-free graphs. This lemma is
the mathematical bridge from that HIT plus a reducible 𝒞 to “no such graph
exists,” hence BK at Δ=9. Until proved, UNAVOIDABLE Claims carry
`[conditional on discharging closure lemma BK.reducible_and_unavoidable_imp_no_counterexample]`.
The D=9 theorem is intentionally *not* `borodinKostochka` (Δ ≥ 9).

## Sanity checks
Empty-graph non-criticality, K₉ not K₉-free, and the K₁₀ arithmetic probe for
`borodinKostochka_at_nine` live in [`SanityChecks.lean`](SanityChecks.lean)
(`example` only; independent of any `sorry` proof). See `docs/TRUST.md`.
