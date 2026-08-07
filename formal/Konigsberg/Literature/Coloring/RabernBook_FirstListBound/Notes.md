# RabernBook_FirstListBound

Book: Landon Rabern, *Basic Graph Coloring*, §"Coloring with prescribed list sizes".

**Statement.** If `|L(v)| > d(v)` for all `v` (i.e. `|L(v)| ≥ d(v)+1`), then `G`
is `L`-colorable — equivalently `FChoosable G (fun v => G.degree v + 1)`.

**Proof.** Greedy induction over a finset of already-coloured vertices. When
adding `a`, the colours used by neighbours already in the set form a set of
size ≤ `deg(a)`, so a list of size ≥ `deg(a)+1` still has a free colour. Same
shape as `Konigsberg.Areas.Coloring.choosable_card`, with the card bound replaced
by the neighbour bound (`map_neighborFinset` / `degree`).

**Why it matters.** The first corpus entry exercising the Literature loop end to
end. Downstream edge-bound entries (`4ListCriticalEdgeBound`, etc.) rest on
`basicIrreducible` from `Areas/Coloring/Irreducible.lean`; this entry is the
greedy seed that appears in the same book section.
