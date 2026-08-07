# KiersteadRabern_OreVizing

**Source.** H. Kierstead & L. Rabern, *Improved lower bounds on the number of
edges in list critical and online list critical graphs*, arXiv:1406.7355.
TeX: [`github.com/landon/Research/OreVizing`](https://github.com/landon/Research/tree/master/OreVizing)
@ `551eea7`. Public domain.

**Claims stated.**
1. `edgeBound_listCritical` — `2‖G‖ ≥ g_k(|G|, c)` for non-complete
   `k`-list-critical `G` (`k ≥ 6`), with `c = (k−3)α_k` (`k ≥ 8`) or
   `(k−4)α_k` (`k ∈ {6,7}`).
2. `oreBrooks_list` — Ore-degree Brooks for choosability:
   `θ ≥ 18`, `ω ≤ θ/2` ⇒ `⌊θ/2⌋`-choosable.

**Lean deps.** `KListCritical`, `Choosable`, `cliqueNum` (mathlib),
`NotCompleteOfOrder` (shared with `Rabern_4ListCriticalEdgeBound`). Online /
AT-critical variants and the general “many edges or f_H-AT subgraph” lemma
are deferred until orientation / paintability land in Areas.
