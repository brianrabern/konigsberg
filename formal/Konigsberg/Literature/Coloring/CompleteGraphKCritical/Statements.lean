/-
CompleteGraphKCritical — K_k is k-critical (non-vacuity witness).

`completeGraph (Fin k)` (= K_k) has χ = k, and every proper subgraph is
(k−1)-colorable, so it satisfies `KCritical k` (`Areas.Coloring.Basic`:
`¬ Colorable (k−1) ∧ ∀ H ≠ ⊤, H.coe.Colorable (k−1)`).

Role: this is the **non-vacuity witness** for the reducibility bridge
(`BK_ReducibleOfFChoosable`, which concludes `KCritical G D → … → False`) and the
discharging closure (`BK_DischargingClosure`). A `⇒ False` lemma is worthless if its
load-bearing hypothesis `KCritical` is unsatisfiable; `K_k` shows it is inhabited for
every `k ≥ 1`. It is also a reusable structural fact.

The theorem `completeGraph_kCritical` is proved in `Proofs.lean` (same namespace).
Spelling is `KCritical (completeGraph (Fin k)) k` — `KCritical` lives in
`Areas.Coloring`, so it is not a `SimpleGraph` field.
-/
import Konigsberg.Literature.Coloring.CompleteGraphKCritical.Proofs

namespace Konigsberg.Literature.Coloring.CompleteGraphKCritical
end Konigsberg.Literature.Coloring.CompleteGraphKCritical
