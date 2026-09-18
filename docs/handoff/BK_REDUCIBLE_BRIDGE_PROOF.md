# Proving `reducible_of_fChoosable` — lemma DAG for Konigsberg

*The reducibility engine mints forbidden-configuration Claims **conditional** on this
bridge lemma. Proving it moves every such Claim from conditional to promotable. The
proof is clean — three sub-lemmas — but the **stated theorem must be repaired first**:
as written it is not provable, because a parameter it counts on is unconstrained. Do the
two statement fixes, then prove the DAG increment by increment against the kernel,
minting `proved` only with clean `#print axioms`.*

The real API (verified against `Areas/Coloring/Basic.lean`):

```
abbrev ListAssignment V := V → Finset ℕ
def IsProperColoring (c : V → ℕ) : Prop := ∀ ⦃u v⦄, G.Adj u v → c u ≠ c v
def ListColorable (L) : Prop := ∃ c, (∀ v, c v ∈ L v) ∧ IsProperColoring G c
def FChoosable (f : V → ℕ) : Prop := ∀ L, (∀ v, f v ≤ (L v).card) → ListColorable G L
theorem colorable_iff_listColorable_const (k) :
    G.Colorable k ↔ ListColorable G (fun _ => Finset.range k)   -- USE THIS for the glue
```

---

## STEP 0 — Repair the statement (blocking; do not skip)

Two problems in the current `Statements.lean`:

**(a) `dG` is unconstrained — the count cannot close.** The proof needs, for each core
vertex `v`, that the number of *outside* neighbours is `G.degree v − (G.induce s).degree
v`, and it needs `reducibilitySlack = (D−1) − dG v + degK v ≤ |L v|`. That inequality
reduces to `G.degree v ≤ dG v`. But `dG : V → ℕ` is a free parameter with **no
hypothesis** linking it to `G.degree`. With `dG` arbitrary (e.g. `dG v = 0`) the slack is
inflated and no list can satisfy it — the theorem is false/unprovable as stated. **Fix:
add the hypothesis**

```
(hdeg : ∀ v ∈ s, G.degree v ≤ dG v)
```

An *upper* bound is exactly right and actually strengthens the result (it forbids every
configuration whose ambient degree is *at most* the spec). In the tool's use `dG v` is the
exact prescribed degree, so `=` — and `≤` covers it. This is the honest general form.

**(b) `hchi : G.chromaticNumber = D` is unused.** The conclusion is `G.Colorable (D−1)`;
the contradiction with `χ = D` lives at the *call site*, not in this lemma. Drop `hchi`
from the statement so the lemma says exactly what it needs: *rest-colorable +
f-choosable ⇒ colorable*. (Keeping it is harmless but it's a decorative hypothesis the
referee's necessity check should — and will — flag.)

Repaired signature:

```lean
theorem reducible_of_fChoosable (D : ℕ) (s : Set V) [DecidablePred (· ∈ s)]
    (dG : V → ℕ) (hdeg : ∀ v ∈ s, G.degree v ≤ dG v)
    (hrest : (G.deleteVerts s).Colorable (D - 1))
    (hf : FChoosable (G.induce s) (fun v : s => reducibilitySlack G D s dG v)) :
    G.Colorable (D - 1)
```

Update `Notes.md` (informal statement + a line recording that `hdeg` is required and
`hchi` was dropped as decorative) and re-run the fidelity `SanityChecks` for this entry.

---

## The math (what the three lemmas prove)

Take a proper `(D−1)`-coloring `c₀` of the rest `G − s`. For each core vertex `v`, its
outside neighbours are already colored; they forbid at most `d_G(v) − degK(v)` colors from
the `(D−1)`-color palette, so `v` keeps a list of size `≥ (D−1) − (d_G(v) − degK(v)) =
reducibilitySlack`. Feed those lists to `hf`; get a proper coloring of the core respecting
them. Glue: the core coloring and `c₀` agree into a proper `(D−1)`-coloring of all of `G`,
because each core vertex's list *excluded* its outside neighbours' colors. Done.

Palette = `Finset.range (D−1)`. Colors `{0,…,D−2}`.

---

## Lemma A — list construction + the cardinality bound (the crux)

Given the rest-coloring `c₀ : V → ℕ` with `∀ v, c₀ v ∈ range (D−1)`, define for `v : s`

```
forbidden v : Finset ℕ := ((G.neighborFinset ↑v).filter (· ∉ s)).image c₀
L v          : Finset ℕ := Finset.range (D − 1) \ forbidden v
```

**Lemma A.** `∀ v : s, reducibilitySlack G D s dG v ≤ (L v).card`.

Proof obligations, in order (each a named helper if it helps Konigsberg):
1. `(L v).card = (D−1) − (forbidden v ∩ range (D−1)).card ≥ (D−1) − (forbidden v).card`
   — `Finset.card_sdiff` / `card_le_card` bookkeeping.
2. `(forbidden v).card ≤ ((G.neighborFinset ↑v).filter (· ∉ s)).card` — `Finset.card_image_le`.
3. `((G.neighborFinset ↑v).filter (· ∉ s)).card = G.degree ↑v − (G.induce s).degree v`
   — split `neighborFinset` by membership in `s`; the in-`s` part has card `(G.induce
   s).degree v` (this is the **induce-degree ↔ ambient-neighbours-in-`s`** bridge; see
   landmine 1). `G.degree v = card of neighborFinset`.
4. Combine with `hdeg` (`G.degree ↑v ≤ dG ↑v`): `(D−1) − dG v + (induce s).degree v ≤
   (D−1) − (G.degree v − (induce s).degree v) ≤ (L v).card`. Natural-subtraction: keep
   everything as `≤` and use `Nat.sub_le_sub` lemmas; watch truncation (landmine 3).

This is the whole difficulty. If Konigsberg stalls, it will be here — pair on obligation 3.

## Lemma B — invoke f-choosability

**Lemma B.** With `L` from Lemma A, `∃ cK : s → ℕ, (∀ v, cK v ∈ L v) ∧ IsProperColoring
(G.induce s) cK`.

Proof: `hf L (fun v => Lemma_A v)` unfolds `FChoosable`/`ListColorable` directly. One line
plus destructuring. (`fun v => Lemma_A v` supplies the `f v ≤ (L v).card` obligation.)

## Lemma C — glue

Define `c' : V → ℕ := fun w => if h : w ∈ s then cK ⟨w, h⟩ else c₀ w`.

**Lemma C.** `IsProperColoring G c'` and `∀ w, c' w ∈ range (D−1)`; hence `G.Colorable
(D−1)` via `(colorable_iff_listColorable_const G (D−1)).mpr ⟨c', …⟩`.

Case an edge `G.Adj u w`:
- both `∉ s`: `c₀` proper on `G.deleteVerts s`; the edge survives deletion (landmine 2), so `c₀ u ≠ c₀ w`.
- both `∈ s`: `cK` proper on `G.induce s`; the edge is an induced-subgraph edge, so `cK ≠`.
- `u ∈ s`, `w ∉ s`: `c' u = cK ⟨u,_⟩ ∈ L u`, which **excludes** `forbidden u ∋ c₀ w`
  (since `w` is an outside neighbour of `u`), so `c' u ≠ c' w = c₀ w`. Symmetric case dual.

Membership in `range (D−1)`: `c₀` values are in `range` by `hrest`; `cK` values are in
`L v ⊆ range (D−1)` by construction. So `c'` lands in `range (D−1)`.

---

## API landmines (check these against the pin before proving — they're where time goes)

1. **`(G.induce s).degree v` vs "neighbours of `↑v` inside `s`."** Confirm the exact
   mathlib relation (`SimpleGraph.induce` on the subtype `s`, its `neighborFinset`/`degree`
   and the map to `G.neighborFinset ↑v ∩ s`). Prove the bridge as its own lemma; don't
   inline it.
2. **`G.deleteVerts s` semantics.** Is it the induced graph on `sᶜ` (subtype) or `G` with
   `s`-vertices isolated on the same `V`? The glue's "both `∉ s`" case needs: a `G`-edge
   with both ends outside `s` is an edge of `G.deleteVerts s`, and `c₀`'s domain matches
   `V`. Adapt `c₀`'s extraction accordingly (a subtype coloring may need lifting to `V`).
3. **Natural-number truncated subtraction.** `(D−1) − dG v` etc. can truncate. Carry
   bounds as `≤` and prefer `Nat.sub_le_sub_left/right`, `Nat.le_sub_iff_add_le` with the
   right side-conditions; avoid rewriting subtraction into a form that silently truncates.
   The `FChoosableZ` (ℤ-valued) API in `Irreducible.lean` exists precisely to sidestep
   this — consider proving Lemma A over `ℤ` via `fChoosableZ_coe` if the ℕ juggling bogs
   down.
4. `DecidablePred (· ∈ s)` and `DecidableEq V` instances thread through `filter`/`image`;
   they're in scope but keep them explicit where elaboration complains.

---

## How to run it (Konigsberg)

Prove **bottom-up**, minting each as its own `proved` Claim (clean `#print axioms`,
whitelist only — no `sorry`, no `native_decide`):

1. the induce-degree bridge (landmine 1) — small, self-contained;
2. Lemma A obligations 1–4, then Lemma A;
3. Lemma B (trivial once A is in hand);
4. Lemma C (the glue) and the final assembly.

Use `lean_search` (`exact?`/`apply?`) on each `Finset.card` obligation before hand-rolling.
Do **not** attempt the whole theorem in one `lean_prove`; that's how it stalls. If a goal
resists after a few `lean_search` rounds — expected at Lemma A obligation 3 — surface it
and we pair on that single goal.

## Acceptance

- Statement repaired: `hdeg` added, `hchi` dropped, `Notes.md` + `SanityChecks` updated.
- `reducible_of_fChoosable` proved, `status.toml` flipped `stated → proved`,
  `#print axioms` clean (whitelist only).
- `reducible_configuration` HIT Claims drop the `[conditional on bridge lemma]` tag once
  the entry is `proved` (verify the tool reads entry status, or update it to).
- The four sub-lemmas land as named, reusable results (they generalize beyond BK).

## Scope

- This proves only the *direct-extension* bridge (f-choosability ⇒ reducible). The
  Kempe-chain strengthening is a separate, later lemma — out of scope here.
- Adding `hdeg` as `≤` (not `=`) is deliberate and correct; don't "simplify" it to `=`.
