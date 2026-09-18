# BorodinKostochka

## Informal statement
Every graph with maximum degree Δ ≥ 9 satisfies χ ≤ max{Δ−1, ω}.
Equivalently: it is (max{Δ−1, ω})-colorable.

## Source
O.V. Borodin, A.V. Kostochka, On an upper bound of a graph's chromatic
number, J. Comb. Theory Ser. B 23 (1977) 247–250.

## Provenance
Agent-drafted stated target for the `--forever` campaign. The conjecture is
open; this entry is the Lean statement the hunt is allowed to prove.

## Fidelity review
- `Colorable (max (maxDegree - 1) cliqueNum)` is χ ≤ max{Δ−1, ω}.
- `9 ≤ maxDegree` is Δ ≥ 9. Lean `Nat` subtraction saturates; under the
  hypothesis `maxDegree - 1` is at least 8.
- This is **not** a proof. `sorry` is required until a kernel proof exists.
- The imported `sorry` declaration cannot be overwritten in the scratch env.
  A campaign proof is a durable `lean_prove` whose `lean_name` contains
  `BorodinKostochka` and whose snippet is this statement with a closed
  proof (no `sorry`). That Claim settles `--forever`.
- Reed's large-Δ theorem is not encoded here.

## Sanity checks
Numeric probes on K₁₀ live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `cliqueNum_completeGraph_fin` only). See `docs/TRUST.md`.
