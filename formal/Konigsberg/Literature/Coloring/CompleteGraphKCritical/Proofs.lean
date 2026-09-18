/-
Proofs for CompleteGraphKCritical: K_k is k-critical.

(1) ¬ Colorable (k−1): K_k is a k-clique, so a (k−1)-coloring is impossible
    (`Colorable.card_le_of_pairwise_adj`).
(2) Every proper subgraph is (k−1)-colorable: omit a vertex (order ≤ k−1) or
    omit an edge (identify the two non-adjacent endpoints).
-/
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.CompleteGraphKCritical

open Finset SimpleGraph
open Konigsberg.Areas.Coloring

/-- K_k is not (k−1)-colorable: the full vertex set is a clique of size k. -/
lemma completeGraph_not_colorable_pred {k : ℕ} (hk : 1 ≤ k) :
    ¬ (completeGraph (Fin k)).Colorable (k - 1) := by
  intro hc
  have hle : Nat.card (Fin k) ≤ k - 1 :=
    hc.card_le_of_pairwise_adj id fun i j hij => by
      simp [completeGraph_eq_top, top_adj, hij]
  simp [Nat.card_eq_fintype_card, Fintype.card_fin] at hle
  omega

/-- A spanning subgraph whose coercion is the complete graph is the top subgraph. -/
lemma subgraph_eq_top_of_verts_univ_coe_top {V : Type*} {G : SimpleGraph V}
    {H : G.Subgraph} (hverts : H.verts = Set.univ) (hcoe : H.coe = ⊤) : H = ⊤ := by
  refine Subgraph.ext hverts (funext₂ fun u v => propext ⟨H.adj_sub, fun hadj => ?_⟩)
  have hu : u ∈ H.verts := hverts ▸ Set.mem_univ u
  have hv : v ∈ H.verts := hverts ▸ Set.mem_univ v
  have : H.coe.Adj ⟨u, hu⟩ ⟨v, hv⟩ := by
    rw [hcoe, top_adj]
    intro h
    exact G.ne_of_adj hadj (congrArg Subtype.val h)
  exact this

/-- Identify the two endpoints of a missing edge; the rest keep distinct colours. -/
lemma colorable_pred_of_coe_ne_top {k : ℕ} {H : (completeGraph (Fin k)).Subgraph}
    (hverts : H.verts = Set.univ) (hne : H.coe ≠ ⊤) :
    H.coe.Colorable (k - 1) := by
  classical
  obtain ⟨a, b, hneab, hnabj⟩ := ne_top_iff_exists_not_adj.mp hne
  let color : H.verts → H.verts := fun x => if x = b then a else x
  have hmem : ∀ x, color x ∈ (univ.erase b : Finset H.verts) := by
    intro x
    refine mem_erase.mpr ⟨?_, mem_univ _⟩
    intro h
    by_cases hx : x = b
    · simp [color, hx] at h
      exact hneab h
    · simp [color, hx] at h
  let C : H.coe.Coloring (univ.erase b) :=
    Coloring.mk (fun x => ⟨color x, hmem x⟩) (by
      intro x y hxy hEq
      have hcol : color x = color y := Subtype.ext_iff.mp hEq
      dsimp [color] at hcol
      by_cases hxb : x = b <;> by_cases hyb : y = b <;> simp [hxb, hyb] at hcol
      · exact H.coe.ne_of_adj hxy (hxb.trans hyb.symm)
      · apply hnabj
        rw [hxb, ← hcol] at hxy
        exact hxy.symm
      · apply hnabj
        rwa [hyb, hcol] at hxy
      · exact H.coe.ne_of_adj hxy hcol)
  refine Colorable.mono ?_ C.colorable
  simp only [Fintype.card_coe]
  rw [card_erase_of_mem (mem_univ b), card_univ]
  have : Fintype.card H.verts = k := by
    rw [Fintype.card_congr ((Equiv.setCongr hverts).trans (Equiv.Set.univ _)),
      Fintype.card_fin]
  omega

/-- Every proper subgraph of K_k is (k−1)-colorable. -/
lemma completeGraph_proper_subgraph_colorable {k : ℕ}
    (H : (completeGraph (Fin k)).Subgraph) (hH : H ≠ ⊤) :
    H.coe.Colorable (k - 1) := by
  classical
  by_cases hverts : H.verts = Set.univ
  · exact colorable_pred_of_coe_ne_top hverts fun htop =>
      hH (subgraph_eq_top_of_verts_univ_coe_top hverts htop)
  · have ⟨v, hv⟩ : ∃ v, v ∉ H.verts := by
      contrapose! hverts
      exact Set.eq_univ_iff_forall.mpr hverts
    have hlt : Fintype.card H.verts < k := by
      simpa [Fintype.card_fin] using Fintype.card_subtype_lt hv
    exact Colorable.mono (Nat.le_sub_one_of_lt hlt) (colorable_of_fintype H.coe)

/-- **K_k is k-critical** in the hereditary sense of `KCritical`: not `(k−1)`-colorable,
and every proper `Subgraph H ≠ ⊤` is `(k−1)`-colorable (vertex-deleted *and* spanning
edge-deleted). Stronger than vertex-criticality alone; for `K_k` the two coincide
with edge-criticality. Folklore; the non-vacuity witness for the BK `⇒ False` bridges. -/
theorem completeGraph_kCritical (k : ℕ) (hk : 1 ≤ k) :
    KCritical (completeGraph (Fin k)) k :=
  ⟨completeGraph_not_colorable_pred hk, completeGraph_proper_subgraph_colorable⟩

end Konigsberg.Literature.Coloring.CompleteGraphKCritical
