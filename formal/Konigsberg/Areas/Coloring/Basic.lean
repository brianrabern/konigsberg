/-
Areas/Coloring — the exemplar vertical. Definitional layer.

THIS IS THE HIGHEST-LEVERAGE, LEAST-AUTOMATABLE WORK AND IS NOT DELEGATED.
A wrong `ListColorable` / `ListCritical` makes true theorems unprovable or
trivially false, and everything downstream inherits the quality of these
definitions. mathlib has essentially NO list-coloring theory, so most of this
must be built by hand and reviewed before any dependent work.

The declarations below are intentionally left as a TODO checklist rather than
guessed definitions — getting them right is a modeling problem for a human, not
scaffold filler. Fill incrementally, each reviewed.
-/
import Mathlib.Combinatorics.SimpleGraph.Coloring
import Konigsberg.Foundations.Basic

namespace Konigsberg.Areas.Coloring

/-
TODO (M2, human-authored, reviewed):
  * ListColoring / ListColorable / choosability number (chₗ)
  * Critical, ListCritical  (vertex- and edge-)
  * low-degree vertices, average degree
  * bad K₂ components, Gallai trees
  * degree-choosability
  * the connecting lemmas that make paper theorems statable
-/

end Konigsberg.Areas.Coloring
