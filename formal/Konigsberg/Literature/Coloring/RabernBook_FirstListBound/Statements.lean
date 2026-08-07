/-
FirstListBound — Rabern, *Basic Graph Coloring*, §"Coloring with prescribed list sizes".

If `|L(v)| > d(v)` for all `v` (equivalently `|L(v)| ≥ d(v)+1`), then `G` is
`L`-colorable: i.e. `G` is pointwise `(d+1)`-choosable.
-/
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.RabernBook_FirstListBound

open Finset Function SimpleGraph
open Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)

/-- If `|L(v)| ≥ deg(v)+1` for every vertex, then `G` is `L`-colorable.
Greedy induction over coloured vertex sets: at `a`, already-coloured neighbours
use at most `deg(a)` colours, so `L a` still has a free colour. -/
theorem firstListBound [Fintype V] [DecidableEq V] [DecidableRel G.Adj] :
    FChoosable G (fun v => G.degree v + 1) := by
  classical
  intro L hL
  suffices h : ∀ s : Finset V, ∃ c : V → ℕ,
      (∀ v ∈ s, c v ∈ L v) ∧ (∀ u ∈ s, ∀ v ∈ s, G.Adj u v → c u ≠ c v) by
    obtain ⟨c, hmem, hproper⟩ := h Finset.univ
    exact ⟨c, fun v => hmem v (mem_univ v),
      fun u v huv => hproper u (mem_univ u) v (mem_univ v) huv⟩
  intro s
  induction s using Finset.induction with
  | empty => exact ⟨fun _ => 0, by simp, by simp⟩
  | @insert a s ha ih =>
    obtain ⟨c, hmem, hproper⟩ := ih
    set bad : Finset ℕ := (s.filter (fun b => G.Adj a b)).image c with hbad
    have hbad_card : bad.card < (L a).card := by
      have hle : bad.card ≤ G.degree a := by
        have h1 : bad.card ≤ (s.filter (fun b => G.Adj a b)).card := card_image_le
        refine h1.trans ?_
        have hsub : s.filter (fun b => G.Adj a b) ⊆ G.neighborFinset a := by
          intro b hb
          exact (mem_neighborFinset _ _ _).mpr (mem_filter.mp hb).2
        exact (card_le_card hsub).trans_eq (card_neighborFinset_eq_degree G a).symm
      have hLa : G.degree a + 1 ≤ (L a).card := hL a
      omega
    have hne : (L a \ bad).Nonempty := by
      rw [← card_pos]
      have := le_card_sdiff bad (L a)
      omega
    obtain ⟨x, hx⟩ := hne
    rw [mem_sdiff] at hx
    obtain ⟨hxL, hxbad⟩ := hx
    refine ⟨update c a x, ?_, ?_⟩
    · intro v hv
      rcases mem_insert.mp hv with rfl | hvs
      · rwa [update_self]
      · rw [update_of_ne (by rintro rfl; exact ha hvs)]; exact hmem v hvs
    · intro u hu v hv huv
      rcases mem_insert.mp hu with (rfl | hus)
      · rcases mem_insert.mp hv with (rfl | hvs)
        · exact absurd huv (G.loopless.irrefl _)
        · rw [update_self, update_of_ne (by rintro rfl; exact ha hvs)]
          intro hc
          exact hxbad (hbad ▸ mem_image.mpr
            ⟨v, mem_filter.mpr ⟨hvs, huv⟩, hc.symm⟩)
      · rcases mem_insert.mp hv with (rfl | hvs)
        · rw [update_of_ne (by rintro rfl; exact ha hus), update_self]
          intro hc
          exact hxbad (hbad ▸ mem_image.mpr
            ⟨u, mem_filter.mpr ⟨hus, huv.symm⟩, hc⟩)
        · rw [update_of_ne (by rintro rfl; exact ha hus),
              update_of_ne (by rintro rfl; exact ha hvs)]
          exact hproper u hus v hvs huv

end Konigsberg.Literature.Coloring.RabernBook_FirstListBound
