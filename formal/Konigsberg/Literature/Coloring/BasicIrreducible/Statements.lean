/-
BasicIrreducible — Literature cite of the green Areas lemmas.

Book: if G is f-irreducible then f(v) ≤ d(v) for all v; in particular 2|E| ≥ f(V).
Already proved in `Areas/Coloring/Irreducible.lean`; this entry surfaces it to
`literature_search` as formalized.
-/
import Konigsberg.Areas.Coloring.Irreducible

namespace Konigsberg.Literature.Coloring.BasicIrreducible

open Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **BasicIrreducible** (book \label{BasicIrreducible}). -/
theorem basicIrreducible (f : V → ℤ) (h : FIrreducible G f) :
    ∀ v, f v ≤ (G.degree v : ℤ) :=
  Konigsberg.Areas.Coloring.basicIrreducible G f h

/-- Handshake form: f-irreducible ⇒ `∑ f ≤ 2|E|`. -/
theorem sum_le_two_mul_card_edgeFinset (f : V → ℤ) (h : FIrreducible G f) :
    ∑ v, f v ≤ 2 * (G.edgeFinset.card : ℤ) :=
  Konigsberg.Areas.Coloring.sum_le_two_mul_card_edgeFinset G f h

end Konigsberg.Literature.Coloring.BasicIrreducible
