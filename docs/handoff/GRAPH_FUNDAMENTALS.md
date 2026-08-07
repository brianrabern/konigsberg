# Graph-theory fundamentals toolkit (Cursor spec)

*The domain-agnostic substrate every graph-theory agent needs — construction, IO,
inspection, invariants, structural operations, relations, generators, and
connectivity — before any coloring is involved. Konigsberg built the sophisticated
coloring/choosability/BK tier first and left the foundation thin: the core `Graph`
class has five methods, there is no way to build or describe a graph, and several
elementary invariants are missing. That gap is the root cause of the agent
fabricating graph6 strings. This spec fills the bottom of the stack.*

`networkx 3.4.2` is installed and is the workhorse for almost all of this — most of
it is wiring, not algorithms. `pysat` is present. `geng` (nauty) is **not** on PATH
and should be installed (WP6).

## Design principles (apply to every tool below)

- **graph6 is the universal handle.** Every tool takes a graph6 string; every tool
  that *produces* a graph returns a **canonical** graph6 string, so tools compose
  (complement → describe → is_isomorphic, etc.). `make_graph` is the one way to
  mint a graph6 — the agent must never hand-write one.
- **JSON-native args, pydantic arg models** (per `AGENT_TOOLUSE.md`); **register
  Lean-free** (all of this is pure Python/networkx — no REPL).
- **Trust roots by cost:** polynomial deterministic invariants →
  `python-checked` (a `computed` root is fine if you prefer). NP-hard invariants
  (α, ω, matching, χ) → **carry a re-checkable witness** (the clique / independent
  set / matching / coloring) → `certificate-checked`. Never mint an NP-hard number
  without its witness.
- **`describe_graph` batches the cheap invariants** into one overview call so the
  agent gets eyes on an input without ten tool calls; individual invariant tools
  exist for when it wants to *establish* one as a ledger Claim.
- **Simple graphs only** (no loops/multiedges) — validate and reject on input,
  consistent with the existing `Graph`/graph6 assumptions.

---

## WP1 — Construction & IO (the root-cause fix)

- **`make_graph(spec) -> Claim`** — the single graph factory. Accepts:
  - **named family + params:** `complete(n)` (K_n), `cycle(n)` (C_n), `path(n)`
    (P_n), `empty(n)`, `star(n)`, `wheel(n)`, `complete_bipartite(m,n)`,
    `complete_multipartite(parts)`, `hypercube(d)` (Q_d), `grid(m,n)`,
    `petersen`, `turan(n,r)`;
  - **`from_edges(n, edges)`** — explicit edge list;
  - **`from_graph6(s)`** — parse/validate an existing string.
  Returns the **canonical graph6** plus a one-line summary (n, m). This is what
  lets the agent say "K₄" or "the Petersen graph" instead of guessing `C~`.
- **`graph6_encode(n, edges) -> str`** / **`graph6_decode(s) -> {n, edges}`** —
  expose the codec directly for round-tripping.
- **Canonicalization:** true canonical labeling needs nauty. If `geng`/`labelg`
  (or `pynauty`) is available, use it; otherwise use a documented deterministic
  relabeling + a Weisfeiler–Lehman hash (`nx.weisfeiler_lehman_graph_hash`) for
  dedup, and `is_isomorphic` (WP5) for exact identity. **State the limitation** in
  the docstring — WL-hash dedup is near-canonical, not provably canonical, without
  nauty.

## WP2 — Inspection

- **`describe_graph(graph6) -> Claim`** — one-shot overview (no establishment of
  hard invariants): order n, size m, degree sequence, δ, Δ, average degree,
  density, connected?, #components, bipartite?, girth, is_tree/forest, is_regular,
  is_planar, and a best-effort "named graph?" match (compare against the WP1
  families up to isomorphism for small n). The agent's default first move on any
  unfamiliar graph6.

## WP3 — Invariants (individual tools; each mintable as a Claim)

Polynomial / deterministic (`python-checked`):
- `order`, `size`, `degree_sequence`, `min_degree`, `max_degree`, `average_degree`
- `is_connected`, `num_components`, `components` (vertex sets),
  `vertex_connectivity`, `edge_connectivity`, `is_k_connected(k)`
- `is_bipartite` (+ the bipartition witness when true)
- `girth`, `diameter`, `radius`, `eccentricity`
- `is_tree`, `is_forest`, `is_regular`, `is_planar` (+ Kuratowski witness if false),
  `is_eulerian`, `has_eulerian_path` *(the namesake — Königsberg)*
- `triangle_count`, `transitivity`
- **`degeneracy` / `k_core_number`** — the most important structural invariant here
  (d-degeneracy ⇒ greedy (d+1)-color/choose bound; backbone of list-coloring and
  the BK neighborhood). Return the degeneracy ordering as witness.

NP-hard (`certificate-checked`, witness mandatory; SAT/enumeration, small-graph
caveat):
- `independence_number` (α) + witnessing independent set
- `clique_number` (ω) + witnessing clique *(already exists — fold in here)*
- `matching_number` + witnessing matching (this one is actually polynomial —
  `nx.max_weight_matching` — so it can be `certificate-checked` cheaply)

## WP4 — Structural operations (graph → graph, return canonical graph6)

Each returns a new graph6 so results compose:
- `complement`
- `induced_subgraph(graph6, vertices)`
- `delete_vertex` / `delete_vertices`, `delete_edge` / `delete_edges`
- `add_edge` / `add_vertex`
- `contract_edge`
- `line_graph`
- `disjoint_union`, `union`, `join`, `cartesian_product`, `tensor_product`
- `k_core(graph6, k)` — the k-core subgraph

## WP5 — Relations between graphs

- `is_isomorphic(g1, g2) -> Claim` (VF2 exact) and `could_be_isomorphic` (fast
  invariant pre-check) for cheap negatives.
- `is_subgraph(host, pattern)` and `is_induced_subgraph(host, pattern)` (+ the
  embedding witness when true).
- `contains_clique(graph6, k)`, `contains_cycle(graph6, length|any)`,
  `contains_path(graph6, length)` — with the witnessing vertex set.

## WP6 — Generators & enumeration

- **Install `geng` (nauty)** on the runtime PATH — enumeration is currently capped
  at the networkx atlas (n ≤ 7). Same class of gap as the earlier `pysat` miss:
  a core dependency missing from the actual runtime. Make it a hard dep or a
  documented setup step, and have enumeration report loudly when it's absent
  (as `bk_search` already does).
- **`enumerate_graphs(n, *, connected=False, min_degree=None, regular=None,
  max_hits=None) -> [graph6]`** — geng when present, atlas fallback for n ≤ 7,
  with the standard filters (these prunings are what make searches tractable).
- **`random_graph(n, p, seed) -> Claim`** — G(n,p), for quick testing/examples
  (clearly marked as a sample, not a search).

## WP7 — Paths, distances, connectivity

- `shortest_path(graph6, u, v)`, `distance(graph6, u, v)`, `neighbors(graph6, v)`
- `bfs_order` / `dfs_order(graph6, root)`
- `spanning_tree(graph6) -> graph6`
- `connected_components` (vertex partition; overlaps WP3 `components` — expose once)

---

## Registration & consistency requirements

- All tools registered in `build_registry`, model-callable, **Lean-free**.
- Uniform contract: graph6 in; Claim out (with witness where applicable);
  graph-producing tools return canonical graph6.
- Add a `/tools` grouping so the ~40 tools are legible by category (construction,
  inspection, invariants, structure, relations, generators, paths, coloring,
  formal, literature) rather than a flat wall.
- Update the system prompt: "To reference a graph, call `make_graph` — never write
  a graph6 string yourself. On an unfamiliar graph6, call `describe_graph` first."
  This closes the fabrication failure mode at the disposition level too.

## Tests

- `make_graph(complete 4)` → canonical graph6 for K₄; `from_edges` round-trips
  through `graph6_encode`/`decode`; `from_graph6("C~")` validates.
- `describe_graph("C~")` → n=4, m=6, 3-regular, connected, not bipartite, girth 3,
  planar, "named: K₄".
- Invariants on known graphs: Petersen → δ=Δ=3, girth 5, α=4, ω=2, degeneracy 3,
  not planar, vertex-connectivity 3; C₅ → bipartite false, girth 5; K_{3,3} →
  bipartite true, not planar.
- Structural: `complement(C~)` = empty graph on 4; `line_graph`, `contract_edge`,
  `induced_subgraph` return correct canonical graph6.
- Relations: `is_isomorphic` between two labelings of C₅ → true; a clique/subgraph
  containment returns the witness.
- NP-hard tools return a witness that independently re-checks.
- `ruff` clean, `pytest` green; existing trust-invariant / grounding tests pass.

## Acceptance

- The agent can construct any standard graph by name or edges, describe any
  graph6 in one call, compute the standard invariants (with witnesses for the hard
  ones), transform graphs compositionally, test isomorphism/containment, enumerate
  a filtered family, and answer basic connectivity/path queries — none of it
  coloring-specific.
- No tool anywhere requires the agent to hand-write a graph6 string.
- `geng` installed; enumeration works past n = 7.

## Scope discipline

- This is the domain-agnostic layer — keep coloring/choosability out of it (those
  tools already exist and stay separate).
- Don't reimplement what networkx provides correctly; wrap it. Reserve custom code
  for the graph6 canonical handle and the certificate extraction.
- NP-hard invariants always carry a witness or the small-graph completeness caveat
  — never a bare number.
- Batch cheap invariants in `describe_graph`; expose individual tools for the ones
  worth minting as Claims. Don't create forty near-duplicate one-liners where a
  grouped call suffices — but every *establishable* invariant needs its own
  Claim-minting tool.
