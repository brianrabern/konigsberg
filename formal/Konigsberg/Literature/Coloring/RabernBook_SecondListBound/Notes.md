# RabernBook_SecondListBound

Book: Landon Rabern, *Basic Graph Coloring*, §"Coloring with prescribed list sizes".

**Statement.** If `G` has an acyclic orientation with `|L(v)| > d⁺(v)` for all
`v` (i.e. `|L(v)| ≥ d⁺(v)+1`), then `G` is `L`-colorable — equivalently
`FChoosable G (fun v => o.outDegree v + 1)`.

**Proof.** Greedy-with-a-sink induction on the remaining vertex set `u`: pick a
sink `a` of `u` (exists by well-foundedness of the reverse-arc relation), colour
it from `L a` (out-degree inside `u` is 0), drop that colour from in-neighbour
lists, and induct on `u.erase a`. Scaffolding (`Orientation`, `outDegree`,
`IsAcyclic`) and the core lemma live in `Areas/Coloring/Orientation.lean`; the
Literature claim is the thin `FChoosable` wrapper in `Statements.lean`.

**Why it matters.** Strengthens `FirstListBound` (recover it by orienting
arbitrarily and using `d⁺ ≤ d`); the same sink induction is the combinatorial
engine behind Kernel Magic / Alon–Tarsi list bounds later in the book.
