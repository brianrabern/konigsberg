# Literature search — make the corpus discoverable (Cursor spec)

*Konigsberg is built on Rabern's work, yet asked "any results by Rabern?" the agent
disclaimed knowledge — because the Literature tier is files it has no tool to read.
Add a retrieval tool over the corpus so the agent can answer what's known, always
with the honest status of each result. This is the `library_map` stub, finally
filled, and it turns Konigsberg from "a prover you feed exact snippets" into "an
assistant you can ask what's established."*

Live evidence:
```
kg> do you [know] any results by Rabern?
Established (ledger): (nothing established)
Commentary: "I don't have access to a database of literature…"
```
False in spirit: `RabernBook_FirstListBound` (formalized), the edge-bound theorems
(stated), and BrooksLean (external-verified) are all right there in the repo.

---

## The honesty problem this must solve

A recorded corpus result is **not** the same as a result established *this session*,
and a `stated` entry is a `sorry` — not proven at all. So the tool must never let
the agent report a catalogued item as freshly established, nor a `stated` theorem as
a theorem. Three status vocabularies already exist on disk and must be preserved,
not flattened:

| On-disk status | Meaning | How the agent may describe it |
|---|---|---|
| `formalized` (`status.toml`) | Proved in-tree, gate-verified (`#print axioms`, no `sorry`) | "formalized in-tree (kernel-verified)" — a real result |
| `stated` (`status.toml`) | Statement only; proof is `sorry` | "**stated only — not yet proven**" — NOT a result |
| `external-verified` (`EXTERNAL.md`) | No-`sorry`/clean axioms under a *different* toolchain | "external-verified (different pin; not in-tree)" |

---

## WP1 — A machine-readable index (`library_map`)

Retrieval needs structured data. `status.toml` files already are; `EXTERNAL.md`
is prose.

- **Build `library_map()`** in the harness: walk
  `formal/Konigsberg/Literature/**/status.toml`, parse each into a record
  `{name, citation, area, claims:[{lean_name, status, verified_at}]}`.
  (Parse TOML with `tomllib`; the repo already shims it for py3.10 — reuse that.)
- **Make externals parseable.** Do NOT scrape `EXTERNAL.md`. Add a companion
  `formal/Konigsberg/Literature/EXTERNAL.toml` as the machine-readable source of
  truth (repo, commit, lean/mathlib pins, each declaration name, `status =
  "external-verified"`, statement, stage-0 date). Keep `EXTERNAL.md` as the human
  doc — ideally generated from, or checked against, the toml so they can't drift.
  `library_map()` merges these in.
- Return a stable, serializable catalog (list of records) — this is the index both
  the tool and any future `/library` view read from.

## WP2 — The agent tool `literature_search`

- **Signature (JSON-native, pydantic args model per `AGENT_TOOLUSE.md`):**
  `literature_search(query: str, *, area: str | None = None, status: str | None = None) -> list[dict]`.
- Case-insensitive match of `query` against name, citation, `lean_name`, and area
  (optionally `Notes.md` text); optional `area`/`status` filters. Rank exact/name
  hits above citation/body hits.
- **Each returned record carries its status verbatim** — `{name, citation,
  lean_name, status, provenance}` where provenance is `verified_at` (in-tree) or
  repo+commit+pin (external). The status field is mandatory and never omitted;
  this is what keeps the answer honest downstream.
- **This tool does NOT mint ledger Claims.** Retrieval ≠ establishment. Looking a
  result up is not the same as the kernel checking it this session, so it must not
  enter the `Established (ledger)` zone (see WP3). It's a corpus fact with its own
  recorded provenance.
- **Register unconditionally** in `build_registry` (it only reads files — no REPL
  needed), alongside the empirical tools, so it works in Lean-free sessions too.

## WP3 — A `References` render zone (extends answer-grounding)

`literature_search` results are neither "established this session" nor mere model
prose — they're catalogued corpus facts. Give them their own zone so the
distinction is visible (this is the natural extension of `ANSWER_GROUNDING.md`'s
two-zone render):

- Render order: **`Established (ledger)`** (this session's minted Claims) →
  **`References (corpus)`** (literature_search hits, each with its status label) →
  **`Commentary`** (prose).
- The `References` zone is generated from the tool results, not model text. Each
  line shows name + status + provenance; a `stated` entry is visibly marked
  "stated only — not yet proven."
- System-prompt rule (add to the grounding rules): when reporting literature, the
  agent must carry the recorded status and must not upgrade it — a `stated` result
  is described as unproven, an `external-verified` result as not-in-tree. Never
  present a catalogued item as established this session.

So "any results by Rabern?" should now yield a `References` block like:
`RabernBook_FirstListBound — formalized (in-tree)`,
`Rabern_4ListCriticalEdgeBound / CranstonRabern_ImprovedEdgeBound / KiersteadRabern_OreVizing — stated only (not yet proven)`,
`BrooksLean (Rabern's Brooks proof) — external-verified (different pin)` — each a
real pointer, none overstated.

---

## Tests

- `library_map()` parses every `status.toml` + `EXTERNAL.toml`; counts match the
  on-disk entries; malformed toml fails loudly.
- `literature_search("Rabern")` returns the book bounds, the edge-bound theorems,
  and the Brooks external entry, each with correct status.
- `literature_search("...", status="formalized")` filters to in-tree-proven only.
- **Honesty regression:** a `stated` entry is never returned with a status implying
  it's proven; assert the status string is carried verbatim.
- Render test: literature hits land in `References`, not `Established`; the ledger
  stays empty when only `literature_search` ran.
- Trust-invariant + answer-grounding tests still pass.

## Acceptance

- `library_map()` + `EXTERNAL.toml` give a structured corpus index (no markdown
  scraping).
- `literature_search` registered, model-callable, works Lean-free, returns
  status-bearing records, mints no Claims.
- The agent answers "what results by Rabern do we have?" with a `References` zone
  that lists them at their true status.
- `ruff` clean, `uv run pytest` green.

## Scope discipline

- Retrieval only — `literature_search` never mints Claims and never changes an
  entry's status. Establishing/proving stays with the Lean tools.
- Don't flatten the status vocabulary; `stated` ≠ `formalized` ≠ `external-verified`
  must survive to the render.
- No fuzzy/embedding search in v1 — plain substring + filters. Add smarter ranking
  only if measurably needed.
- One new render zone; keep it simple text/Rich, consistent with the existing two.
