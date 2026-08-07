# CranstonRabern_ImprovedEdgeBound

**Source.** D. Cranston & L. Rabern, *Edge lower bounds for list critical
graphs, via discharging*, arXiv:1602.02589. TeX:
[`ImprovedEdgeBound/EdgeBoundDischargingFinal.tex`](https://github.com/landon/Research/tree/master/ImprovedEdgeBound)
@ `551eea7`. Public domain.

**Claims stated.**
1. `mainCor` — `k`-AT-critical, `k ≥ 7`, `G ≠ K_k` ⇒
   `d(G) ≥ k−1 + (k−3)(2k−5)/(k³+k²−15k+15)`.
2. `minorCor` — same for `k ∈ {5,6}` with denominator `k³+2k²−18k+15`.

**AT stub.** `IsKATCritical` is an empty typeclass pending an Alon–Tarsi number
in Areas. The published theorems are about AT-critical graphs (which imply
list-critical bounds via `χ ≤ χ_ℓ ≤ AT`); do not silently weaken the hypothesis
to `KListCritical`.

**Deps.** Discharging + Gallai-tree average-degree bounds; Kernel Magic /
`mic` from the OreVizing / 4ListCritical line.
