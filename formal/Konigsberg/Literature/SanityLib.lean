/-
Shared helpers for Literature `SanityChecks.lean` modules.

Tiny `decide`/`norm_num` probes need `cliqueNum` of `K_n` as a numeral; mathlib's
`cliqueNum` does not reduce under `decide`, so we prove the equality once here.
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Mathlib.Combinatorics.SimpleGraph.Finite

namespace Konigsberg.Literature.SanityLib

open Finset SimpleGraph

/-- `ω(K_n) = n` for `n ≥ 1`. -/
theorem cliqueNum_completeGraph_fin (n : ℕ) [NeZero n] :
    (completeGraph (Fin n)).cliqueNum = n := by
  apply le_antisymm
  · obtain ⟨s, hs⟩ := (completeGraph (Fin n)).exists_isNClique_cliqueNum
    have hcard : s.card ≤ Fintype.card (Fin n) := card_le_univ s
    simpa [hs.card_eq, Fintype.card_fin] using hcard
  · have h : (completeGraph (Fin n)).IsClique (univ : Finset (Fin n)) := by
      intro u _ v _ huv
      exact huv
    simpa [card_univ, Fintype.card_fin] using h.card_le_cliqueNum

end Konigsberg.Literature.SanityLib
