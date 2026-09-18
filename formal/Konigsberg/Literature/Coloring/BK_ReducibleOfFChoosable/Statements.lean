/-
BK_ReducibleOfFChoosable — bridge lemma for the reducible-configuration engine.

Minimal-counterexample form (proved in `Proofs.lean`):
if `G` is `D`-critical (`KCritical G D`), `s` is a nonempty core, `dG` upper-bounds
the ambient degree on all vertices, and the induced core `G.induce s` is
`FChoosableZ` for the reducibility demand
  `f(w) = (D − 1) − (d_G(w) − deg_{G[s]}(w))`  (spelled inline over ℤ),
then `False`. I.e. no such `G` exists — the configuration is forbidden in a minimal
BK counterexample.

Three deliberate choices, all load-bearing (see Notes.md / the proof handoff):
  * Conclusion is `False`, not `Colorable (D−1)`: criticality is folded into the
    hypotheses, so the lemma is the forbidden-configuration statement directly. The
    positive "rest-colorable ⇒ colorable" form is an internal step, not the target.
  * The demand is ℤ-valued (`FChoosableZ`) and written INLINE, not via a bespoke ℕ
    `reducibilitySlack`, precisely to avoid ℕ truncation at `D = 0`, which would
    silently misstate the demand. Do not reintroduce an ℕ slack def.
  * `dG` is generalized with a lower bound `∀ v, G.degree v ≤ dG v` (not `= G.degree`);
    `FChoosableZ` is antitone in the demand, so this is strictly stronger and
    specializes to `dG := G.degree` by `le_refl`. `s.Nonempty` is required — it is
    what makes `sᶜ` a proper subgraph so criticality applies.

The theorem `reducible_of_fChoosable` is defined and proved in `Proofs.lean`
(same namespace); this module re-exports it by import. Do not re-declare it here.
-/
import Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable.Proofs

namespace Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable
end Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable
