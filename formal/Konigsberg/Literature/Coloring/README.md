# Literature/Coloring

Formalized literature as Lean, one entry per `<Author_Result>/` directory. Copy
`templates/new-literature-entry/` to add one.

A `stated` entry (statement typechecks, proof is `sorry`) is first-class: usable
as an explicit hypothesis, `decide`-checkable on small cases, and an open
invitation to contribute the proof. Every entry carries a `status.toml`.

## Corpus (edge-bound / list-critical line)

| Entry | Status | Source |
|---|---|---|
| `RabernBook_FirstListBound` | formalized | *Basic Graph Coloring* |
| `RabernBook_SecondListBound` | formalized | *Basic Graph Coloring* |
| `Rabern_4ListCriticalEdgeBound` | stated | Research/`4ListCriticalEdgeBound` (EJC 2016) |
| `KiersteadRabern_OreVizing` | stated | Research/`OreVizing` (arXiv:1406.7355) |
| `CranstonRabern_ImprovedEdgeBound` | stated | Research/`ImprovedEdgeBound` (arXiv:1602.02589) |
