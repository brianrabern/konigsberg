# Reed_BKLargeDelta

## Informal statement
There is a threshold `Δ₀` such that every finite graph with maximum degree `Δ ≥ Δ₀` and
clique number `ω < Δ` satisfies `χ ≤ Δ − 1`. I.e. the Borodin–Kostochka conjecture holds
for all sufficiently large maximum degree.

## Source
B. Reed, *A strengthening of Brooks' theorem*, J. Combin. Theory Ser. B 76 (1999)
136–149. Explicit constructive constant (`Δ ≥ 5.2·10⁹`): *On the Borodin–Kostochka
conjecture for graphs with large maximum degree*, arXiv:2603.16670.

## Provenance
Agent-drafted **cited frame**. Statement written against the corpus API; **not**
formalized — proof is `sorry` by design.

## Role (why this entry exists)
This is the "what's already known" frame. BK is settled for large Δ, so the live regime —
and the campaign's real target — is small Δ, specifically **Δ = 9**. Having Reed stated
lets the mission/staircase say "large Δ is done; work Δ = 9" and lets a future argument
cite it as a boundary. It is a frame, not a target.

## ⚠️ Do not
- Do **not** make this a proving target. Formalizing Reed's proof is a major project,
  out of scope; the campaign must never spend circuits "proving" it.
- Do **not** promote to `formalized` without an actual Lean proof of Reed. It stays
  `stated`.
- It cannot be laundered into a BK proof: any kernel term citing this `sorry` lemma
  carries `sorryAx`, which both the axiom gate and the campaign settlement check reject.

## Fidelity review
`∃ Δ₀, ∀ G, Δ₀ ≤ Δ(G) → ω(G) < Δ(G) → χ(G) ≤ Δ(G) − 1`. `ω < Δ` is the `K_Δ`-free
hypothesis in the `Δ ≥ Δ₀` regime (where `max{Δ−1, ω} = Δ−1`), matching
[[BorodinKostochka]]'s conclusion on that regime. The existential `Δ₀` is universal over
graphs — quantify `G` inside the `∃`, not before it.

## Sanity checks
[`SanityChecks.lean`](SanityChecks.lean): a non-vacuous instance of the `ω < Δ` regime
whose conclusion holds (`K_{1,3}` is 2-colorable). See `docs/TRUST.md`.
