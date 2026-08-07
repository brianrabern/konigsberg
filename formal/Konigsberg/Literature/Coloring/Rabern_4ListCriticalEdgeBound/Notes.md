# Rabern_4ListCriticalEdgeBound

**Source.** Landon Rabern, *A better lower bound on average degree of
4-list-critical graphs*, Elec. J. Combin. (2016). Public-domain TeX:
[`github.com/landon/Research/4ListCriticalEdgeBound`](https://github.com/landon/Research/tree/master/4ListCriticalEdgeBound)
(commit `551eea7…`; prefer `4ListCriticalEdgeBound_ejc.tex`).

**Main Theorem.** Every non-complete `k`-list-critical graph has
`d(G) ≥ k − 1 + (k − 3)/(k² − 2k + 2)`. For `k = 4` this is `3.1`, the first
improvement on Gallai’s `3 + 1/13` for 4-list-critical graphs.

**Kernel Magic** (Kierstead–Rabern arXiv:1512.08130).  
`2‖G‖ ≥ (k−2)|G| + mic(G) + 1` for every `k`-list-critical `G`.

**Lean dependencies.**
- `KListCritical` — already in `Areas/Coloring/Basic` (Cranston–Rabern form).
- `basicIrreducible` / f-irreducibility — seed of the edge-bound program; not
  yet invoked in the *statement*, but the paper’s proof uses the classical
  list-critical package (Gallai trees on deg-`(k−1)` vertices) that sits
  downstream of the same foundation.
- Still missing for a proof: Gallai-tree formalization, `β_k`, and a
  formalized Kernel Magic (needs independent-set / cut-size machinery —
  stubbed here as `mic` / `cutSize`).

**Status.** Statements typecheck with `sorry`; first substantial edge-bound
Literature entry after `FirstListBound` + `Irreducible.lean`.
