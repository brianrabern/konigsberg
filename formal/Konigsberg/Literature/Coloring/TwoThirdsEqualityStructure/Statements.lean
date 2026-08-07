/-
TwoThirdsEqualityStructure — stated.

ω ≥ (2/3)(Δ+1), X_𝒬 connected ⇒ either ⋂𝒬 ≠ ∅, or Δ(X_𝒬) ≤ 2 with the
pairwise intersection geometry in the book.
-/
import Konigsberg.Areas.Coloring.CliqueCollection
import Mathlib.Combinatorics.SimpleGraph.Connectivity.Connected

namespace Konigsberg.Literature.Coloring.TwoThirdsEqualityStructure

open Finset SimpleGraph Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- Geometric alternative in the equality case (gct bullet 2).

`Δ(X_𝒬) ≤ 2` is encoded as: any three neighbours of a vertex are not pairwise
distinct. Half-ω intersections are stated as `2 * |A ∩ B| = ω` (avoids ℕ
floor). -/
def TwoThirdsGeometry (𝒬 : Set (Finset V)) : Prop :=
  let X := cliqueIntersectionGraph 𝒬
  (∀ (Q A B C : 𝒬), X.Adj Q A → X.Adj Q B → X.Adj Q C → A = B ∨ A = C ∨ B = C) ∧
    ∀ ⦃A B C : 𝒬⦄, X.Adj A B → X.Adj A C → B ≠ C →
      ((B : Finset V) ∩ (C : Finset V) = ∅) ∧
        2 * #((A : Finset V) ∩ (B : Finset V)) = G.cliqueNum ∧
        2 * #((A : Finset V) ∩ (C : Finset V)) = G.cliqueNum

/-- **TwoThirdsEqualityStructure** (gct \\label{TwoThirdsEqualityStructure}).

Line-by-line vs gct: collection of max cliques (`hQ`); ω ≥ (2/3)(Δ+1) as
`3ω ≥ 2(Δ+1)`; X_𝒬 connected; conclusion ∩ ≠ ∅ **or** (Δ(X)≤2 and for distinct
neighbours B,C of A: B∩C=∅ and |A∩B|=|A∩C|=½ω). Arbitrary nonempty-useful
subcollections — book says “a collection,” and Kostochka applies related lemmas
to subcollections; connectedness of X_𝒬 makes the empty case idle. -/
theorem twoThirdsEqualityStructure (𝒬 : Set (Finset V))
    (hQ : 𝒬 ⊆ maxCliqueCollection G)
    (hω : 3 * G.cliqueNum ≥ 2 * G.maxDegree + 2)
    (hconn : (cliqueIntersectionGraph 𝒬).Connected) :
    (⋂ Q ∈ 𝒬, (Q : Set V)).Nonempty ∨ TwoThirdsGeometry G 𝒬 := by
  sorry

end Konigsberg.Literature.Coloring.TwoThirdsEqualityStructure
