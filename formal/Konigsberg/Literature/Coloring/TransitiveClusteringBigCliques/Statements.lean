/-
TransitiveClusteringBigCliques — stated.

Connected vertex-transitive G with ω ≥ (2/3)(Δ+1): either X_𝒬 is edgeless, or
X_𝒬 is a cycle and G is the clique blow-up of that cycle by K_{ω/2}.
-/
import Konigsberg.Areas.Coloring.CliqueCollection
import Mathlib.Combinatorics.SimpleGraph.Circulant

namespace Konigsberg.Literature.Coloring.TransitiveClusteringBigCliques

open Finset SimpleGraph Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- `G` is vertex-transitive. -/
def IsVertexTransitive : Prop :=
  ∀ u v : V, ∃ f : G ≃g G, f u = v

/-- Book’s second alternative: `X_𝒬 ≃ C_n` and `G` is obtained from that cycle
by blowing each vertex up to a `K_{ω/2}` (i.e. `G ≃ cliqueBlowup C_n (ω/2)`). -/
def IsCycleBlowupOfHalfOmega (𝒬 : Set (Finset V)) : Prop :=
  ∃ n : ℕ, 3 ≤ n ∧ Even G.cliqueNum ∧
    Nonempty (cliqueIntersectionGraph 𝒬 ≃g cycleGraph n) ∧
    Nonempty (G ≃g cliqueBlowup (cycleGraph n) (G.cliqueNum / 2))

/-- **TransitiveClusteringBigCliques** (gct \\label{TransitiveClusteringBigCliques}).

`𝒬` is the *full* max-clique collection (book: “the collection of all maximum
cliques”). -/
theorem transitiveClusteringBigCliques
    (hconn : G.Connected) (hvt : IsVertexTransitive G)
    (hω : 3 * G.cliqueNum ≥ 2 * G.maxDegree + 2) :
    let 𝒬 := maxCliqueCollection G
    (cliqueIntersectionGraph 𝒬).edgeSet = ∅ ∨
      IsCycleBlowupOfHalfOmega G 𝒬 := by
  sorry

end Konigsberg.Literature.Coloring.TransitiveClusteringBigCliques
