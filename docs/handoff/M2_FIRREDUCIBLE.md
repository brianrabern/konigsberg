# M2 next increment — f-irreducibility + first Literature entry (Cursor spec)

*`Basic.lean` is green. This adds Rabern's PRIMARY criticality notion —
f-reducible / f-irreducible over a G-numbering — plus `BasicIrreducible` (the seed
of every list-critical edge bound) and the first `Literature` theorem
(`FirstListBound`). Source: `basic graph coloring.tex`, §"Coloring with prescribed
list sizes"; see `COLORING_BOOK_ROADMAP.md`.*

## Where it goes

New file **`formal/Konigsberg/Areas/Coloring/Irreducible.lean`** — `import
Konigsberg.Areas.Coloring.Basic`. Leave the green `Basic.lean` untouched. Add the
new file to the import surface (`Konigsberg.lean` / area root) as the others are.

Everything below is the intended math; write it against mathlib v4.31 and expect
one REPL pass (the `SimpleGraph.induce` subtype handling is the fragile part).

## Definitions (translate faithfully)

Work with `[Fintype V] [DecidableRel G.Adj]` (degrees needed throughout).

1. **G-numbering** — `f : V → ℤ` with `f v ≤ G.degree v + 1` for all `v`. Note ℤ,
   not ℕ: the restriction `f_H` below can go ≤ 0, and that must be representable.
   ```
   def IsGNumbering (f : V → ℤ) : Prop := ∀ v, f v ≤ (G.degree v : ℤ) + 1
   ```

2. **ℤ-valued choosability** (the existing `FChoosable` is ℕ-valued; the numbering
   context needs ℤ, where `f v ≤ 0` correctly forces "not choosable" because an
   empty list is then admissible):
   ```
   def FChoosableZ (f : V → ℤ) : Prop :=
     ∀ L : ListAssignment V, (∀ v, f v ≤ (L v).card) → ListColorable G L
   ```
   (`(L v).card : ℕ` coerces to ℤ.) Sanity lemma to include:
   `FChoosableZ G (fun v => (g v : ℤ)) ↔ FChoosable G g` for `g : V → ℕ`.

3. **Induced restriction `f_H`.** For `s : Set V` (with `[DecidablePred (· ∈ s)]`
   or a `Finset`), the induced subgraph is `G.induce s : SimpleGraph ↥s`. Define,
   for `w : ↥s`,
   ```
   f_H(w) = f w.val - ((G.degree w.val : ℤ) - (G.induce s).degree w)
   ```
   i.e. `f` minus the number of edges from `w` leaving `s` (= `d_G(w) − d_H(w)`).
   This mirrors the book's `f_H(v) = f(v) − |v, G−H|`.

4. **f-reducible / f-irreducible.** `G` is *f-reducible* if some **nonempty**
   induced subgraph `H = G.induce s` is `f_H`-choosable; *f-irreducible* if not.
   The quantifier ranges over ALL nonempty induced subgraphs, `s = univ`
   included.
   ```
   def FReducible (f : V → ℤ) : Prop :=
     ∃ s : Set V, s.Nonempty ∧ FChoosableZ (G.induce s) (fun w => f_H s f w)
   def FIrreducible (f : V → ℤ) : Prop := ¬ FReducible G f
   ```

## Lemma to prove: `BasicIrreducible`

```
theorem basicIrreducible (f : V → ℤ) (h : FIrreducible G f) :
    ∀ v, f v ≤ (G.degree v : ℤ)
```
**Proof (single-vertex reduction).** Suppose `f v ≥ d(v)+1` for some `v`. Take
`s = {v}`. Then `H = G.induce {v}` has no edges, so `(G.induce {v}).degree ⟨v,_⟩ =
0` and `f_H(⟨v,_⟩) = f v − d(v) ≥ 1`. A single vertex with a list of size ≥ 1 is
colorable, so `H` is `f_H`-choosable ⇒ `G` is f-reducible to `H` ⇒ contradiction.
Hence `f v ≤ d(v)`. Corollary worth stating:
`2 * G.edgeFinset.card ≥ ∑ v, f v` (handshake + `basicIrreducible`).

The single-vertex-colorable step is the only fiddly bit — the induced graph on a
singleton is edgeless, so any color in the (nonempty) list works.

## First Literature entry: `FirstListBound`

The first entry proper. Book: *"If `|L(v)| > d(v)` for all `v`, then `G` is
`L`-colorable."* i.e. `G` is `(d+1)`-choosable pointwise:
```
theorem firstListBound : FChoosable G (fun v => G.degree v + 1)
```
Provable now by the **same greedy induction as `Basic.choosable_card`** (each
vertex has more colors than already-colored neighbors). Reuse that proof
structure.

Place as a real `Literature` entry so the corpus loop is exercised end to end:
```
formal/Konigsberg/Literature/Coloring/RabernBook_FirstListBound/
  Statements.lean   -- namespace Konigsberg.Literature.Coloring.RabernBook_FirstListBound
  Proofs.lean       -- the greedy proof (no sorry)
  status.toml       -- status="formalized"; cite basic graph coloring.tex §prescribed list sizes
  Notes.md
```
Copy `templates/new-literature-entry/`. `status.toml` must satisfy `check_status`
(namespace under `Konigsberg.Literature.`, `axioms=[]` field present) and, once
`--run-lean` runs, `check_axioms` (clean axioms — greedy proof uses none beyond
the whitelist).

## Acceptance

- `lake build` green (Irreducible.lean + the Literature entry).
- `basicIrreducible` and `firstListBound` proven — **no `sorry`**.
- `python ci/check_status.py formal` and `check_axioms` pass on the new entry;
  entry's `status.toml` says `formalized` with clean axioms.
- Remove the "next increment" NOTE block from `Basic.lean` once these land
  (its content is now realized here).

## Likely REPL friction (zero in on these)

- `SimpleGraph.induce s` vertex type is `↥s`; degree on it needs
  `Fintype ((G.induce s).neighborSet w)` — may need `[Fintype V][DecidableRel]`
  to propagate, or a local instance.
- `(G.induce s).degree` vs `G.degree w.val` relationship — there may be a mathlib
  lemma (`SimpleGraph.induce` degree/adj lemmas); Loogle for it before proving by
  hand.
- ℤ/ℕ coercions in `FChoosableZ` (`Int.ofNat_le`, `omega`).
- `s.Nonempty` for the singleton `{v}` (`Set.singleton_nonempty`).

## After this

Unblocks the edge-bound corpus: `4ListCriticalEdgeBound`, `ImprovedEdgeBound`,
`OreVizing` (from `github.com/landon/Research`, per `RESEARCH_REPO_MINING.md`) —
all downstream of `basicIrreducible`.
