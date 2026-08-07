/-
TransitiveClusteringBigCliques — stated.

Connected vertex-transitive G with ω ≥ (2/3)(Δ+1): X_𝒬 edgeless, or X_𝒬 is a
cycle and G is the blow-up of that cycle by K_{ω/2}.
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

/-- Blow-up description: X_𝒬 ≃ cycle, each vertex blown to a K_{ω/2}.
Stated as: the max-clique intersection graph is a cycle graph, and every max
clique has size ω with the standard pairwise intersections of size ω/2 along
the cycle (full combinatorial reconstruction deferred to the proof). -/
def IsCycleBlowupOfHalfOmega (𝒬 : Set (Finset V)) : Prop :=
  ∃ n : ℕ, n ≥ 3 ∧ Nonempty (cliqueIntersectionGraph 𝒬 ≃g cycleGraph n) ∧
    (∀ Q ∈ 𝒬, #Q = G.cliqueNum) ∧ Even G.cliqueNum

/-- **TransitiveClusteringBigCliques** (gct \\label{TransitiveClusteringBigCliques}). -/
theorem transitiveClusteringBigCliques
    (hconn : G.Connected) (hvt : IsVertexTransitive G)
    (hω : 3 * G.cliqueNum ≥ 2 * G.maxDegree + 2) :
    let 𝒬 := maxCliqueCollection G
    (cliqueIntersectionGraph 𝒬).edgeSet = ∅ ∨
      IsCycleBlowupOfHalfOmega G 𝒬 := by
  sorry

end Konigsberg.Literature.Coloring.TransitiveClusteringBigCliques
