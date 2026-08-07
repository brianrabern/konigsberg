# Close the agent loop (Cursor spec)

*Unstub the two remaining architectural pieces — a real model provider and the
empirical↔formal bridge — and add a thin end-to-end demo. After this, Konigsberg
runs as an agent you point at a question, not just an instrument you drive by
hand. None of this is research; it's wiring behind interfaces that already exist.*

The trust invariant is untouched: the loop already guarantees only tool-minted
Claims enter the ledger (`test_agent.py::test_lying_final_mints_nothing`). A real
provider does not weaken that — a fluent model still cannot mint a Claim.

---

## WP1 — Real model provider (`models.py`)

The `Model` protocol and `Tier` enum exist; `ModelRouter.complete` is the stub.
Add a concrete provider behind the protocol; keep the scripted fake for tests.

- **`AnthropicModel(Model)`** (new, in `models.py` or `models/anthropic.py`):
  - Reads the key from the environment ONLY (`ANTHROPIC_API_KEY`); never from a
    file or argument. Raise a clear error if missing.
  - `import anthropic` lazily (it's the optional `providers` extra); clear error
    if absent.
  - Tier → model-id map, configurable via constructor/env with defaults; do NOT
    bury brittle model strings deep in logic. Sensible defaults: `CHEAP` → a
    Haiku, `FRONTIER` → a frontier model. Record the chosen IDs on the instance.
  - `complete(prompt, *, tier) -> str`: pick the model by tier, call
    `client.messages.create(...)`, return the concatenated text. Keep it a single
    stateless call — the loop owns the conversation/transcript.
- **Keep `ModelRouter`** as the tier-routing policy wrapper OR fold routing into
  `AnthropicModel`; either way the loop still depends only on `Model`.
- **Tests** (`tests/test_models.py`, no network): monkeypatch the anthropic
  client with a fake; assert (a) `tier=CHEAP` vs `FRONTIER` selects the right
  model id, (b) the prompt is passed through and text returned, (c) missing key
  raises. Add an optional `skipif not os.getenv("ANTHROPIC_API_KEY")` live smoke
  that does one real cheap call.

Note (open decision #5): the cheap/frontier split is the policy — cheap for
empirical dispatch/triage, frontier for proof search. Thresholds can stay simple
(tier is chosen by the caller/loop per step); don't over-engineer routing now.

---

## WP2 — The bridge (`bridge.py`)

The one place the tiers meet. Scope it honestly (the docstring already does):
`decide` over `SimpleGraph` blows up in the kernel past tiny n, and
`native_decide` is not whitelisted. So the bridge's *formal* path is for **finite
witnesses on small graphs**, not for deciding choosability in Lean.

Three pieces:

1. **`export_graph_to_lean(graph, name="G") -> str`** (pure; unit-testable now).
   Emit Lean source for `<name> : SimpleGraph (Fin n)` via
   `SimpleGraph.fromEdgeSet {s(i,j), ...}` over the graph's edges (0-indexed →
   `Fin n` numerals). `fromEdgeSet` auto-symmetrizes and drops the diagonal.
   Flag the fragile bit for the REPL pass: `decide`/`DecidableRel G.Adj` on the
   result may need an explicit `instance`/`inferInstance` — verify once.
2. **`roundtrip_check(graph, repl) -> bool`** (live-Lean; the CI guard the
   docstring demands). Export, send through the REPL, and read the adjacency back
   — e.g. `#eval` the list `[G.Adj i j | i < j]` (or `G.edgeFinset`), parse the
   REPL output, assert it equals the input edge set under the identity labeling
   (we control the numbering, so equality — stronger than isomorphism — is the
   right invariant). Skip when no Lean toolchain.
3. **`verify_coloring(graph6, coloring) -> Claim`** (agent-callable; the honest
   crossing). Given a concrete coloring `c : V → ℕ` (e.g. an empirical witness),
   export the graph and check *this specific function* is a proper coloring via
   `decide` on a concrete, quantifier-free proposition (cheap — no blowup). On
   success mint a **`proved`** Claim (Lean kernel re-checked the witness);
   carry `#print axioms`. This is the real empirical→formal instance: the
   empirical tier finds a witness, the bridge re-checks it in the kernel.
   Do **NOT** attempt `decide` on `G.Colorable k` (quantifies over all
   colorings — blows up / not the point). Checking a *given* coloring is the
   decidable, cheap, honest thing.

Tests: encoder string-shape (pure, now); `roundtrip_check` + `verify_coloring`
as live-Lean tests (skip without a build), plus a `tests/differential/`
round-trip property test over small `all_graphs(n)` graphs.

---

## WP3 — End-to-end demo (prove the loop closes)

- **`scripts/agent_demo.py`**: build `build_registry(repl)`, construct the model
  (real `AnthropicModel` if `ANTHROPIC_API_KEY` present, else the scripted fake),
  run `Agent.run(task)` on a small real task (e.g. "decide whether C5 is
  2-choosable and record the result"), print the resulting ledger. This is the
  demonstrable "model → tool → provenance-stamped ledger" path.
- **`tests/test_agent_e2e.py`**: with the scripted model + a stub REPL, drive one
  full loop that calls `choosability_refute` (or `verify_coloring`) and asserts
  the ledger ends with a Claim of the expected trust root. (Real-provider run is
  the manual `agent_demo`; CI stays offline.)

---

## Acceptance

- `models.py`: `AnthropicModel` behind `Model`; key from env only; tier→id map;
  offline tests green; optional live smoke.
- `bridge.py`: `export_graph_to_lean` + `roundtrip_check` + `verify_coloring`
  implemented; encoder tested offline; roundtrip/verify tested live; differential
  round-trip test added.
- `verify_coloring` registered in `build_registry` (JSON-native args → agent can
  call it); mints `proved` on a re-checked witness.
- `scripts/agent_demo.py` runs end-to-end (scripted offline; real with a key).
- `ruff` clean, `uv run pytest` green, trust invariant test still passes.

## Scope discipline (don't overreach)

- No `decide`-on-`Colorable`; witness-checking only (the honest bridge).
- Don't build a routing DSL; tier is a per-call arg.
- Provider stays behind `Model` — the loop and all tests remain provider-agnostic.
- Model IDs are config, not constants baked into logic (they change).
