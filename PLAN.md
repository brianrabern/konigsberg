# Konigsberg — Project Plan

*A research assistant for graph theory, grounded in formal verification.*

---

## 1. What this is

Konigsberg is an agentic research assistant for graph theory. The LLM is the reasoning core, but the value is the **harness**: deterministic tooling, a formally verified library, and an epistemic ledger that makes every claim traceable to how it was established.

Three things distinguish it from a general coding agent:

1. **Deterministic ground truth.** Verification is Lean's typechecker plus an axiom gate — not an LLM evaluator. Coding agents verify probabilistically; Konigsberg verifies mechanically.
2. **Dual-tier reasoning.** A fast empirical tier (enumeration, SAT, specialized coloring solvers) kills bad conjectures cheaply; a formal tier proves what survives. A bridge moves objects between them.
3. **Literature as code.** The reference corpus is Lean formalizations of theorems and methods, not PDFs — statements usable as hypotheses even before their proofs are formalized.

**Tagline:** *Konigsberg — formal and empirical tools for graph theory research.*

---

## 2. Goals and non-goals

### Goals
- Make a working graph theorist materially faster at: testing structural lemmas, killing false sub-conjectures, and maintaining a verified corpus of surrounding theory.
- Build **graph coloring** as the exemplar vertical — full stack, end to end — as a template other areas copy.
- Establish a trust model rigid enough that a mathematician can rely on the tool's claims.

### Explicit non-goals (v1)
- **Autonomous proof of open conjectures.** Borodin–Kostochka is the north star, not the spec. The tool accelerates a human attack; it does not replace one.
- **Autoformalization of arbitrary papers.** Formalizing one research paper is months of expert work. Statements first, proofs incrementally.
- **Interactive graph-drawing UI.** Deferred. Headless agent + library first.
- **General graph theory coverage at launch.** Coloring only; other areas follow the template.

### The honest framing
> BK will not be proved by pointing an agent at mathlib. It will be proved by a human with dramatically better instruments. Konigsberg is the instrument.

---

## 3. Architecture

Four tiers, one seam between them.

```
┌─────────────────────────────────────────────────────────┐
│  HARNESS (Python)  — agent loop, tool registry,          │
│                      context surfacing, epistemic ledger │
└───────────────┬─────────────────────────┬───────────────┘
                │                         │
     ┌──────────▼──────────┐   ┌──────────▼──────────────┐
     │  FORMAL TIER (Lean) │   │  EMPIRICAL TIER (Python)│
     │  mathlib + own lib  │◄──┤  enumeration, SAT,      │
     │  + formalized lit   │   │  choosability solvers   │
     └─────────────────────┘   └─────────────────────────┘
                    ▲  BRIDGE: graph objects  ▲
                    └──── move both ways ─────┘
```

### Design principles
- **The agent proposes; the gate accepts.** The model can be as creative and unreliable as it likes, because acceptance is mechanical and incorruptible.
- **Never blur epistemic status.** "Python-checked" ≠ "solver-certified" ≠ "proved in Lean" ≠ "conjectured." Every claim carries its provenance.
- **Simple loop, rich tools.** A while-loop dispatching to a tool registry. No orchestration graphs, no multi-agent architecture in v1.
- **Core/periphery.** You own the frame (harness, Foundations, CI gates); the community contributes areas and literature entries against fixed contracts.

---

## 4. Repository layout

Monorepo. Lean and Python live in sibling top-level directories and never import each other — the harness is the only thing that talks to both, via subprocess.

```
konigsberg/
├── README.md
├── LICENSE                      # Apache 2.0 (Landon's reuse terms cleared)
├── CONTRIBUTING.md
├── lean-toolchain
│
├── formal/                      # ── FORMAL TIER (Lean) ──
│   ├── lakefile.toml            # mathlib pinned by commit
│   ├── lake-manifest.json
│   ├── Konigsberg.lean
│   └── Konigsberg/
│       ├── Foundations/         # CORE — area-agnostic, human-owned
│       ├── Areas/
│       │   └── Coloring/        # exemplar vertical
│       │       ├── Basic.lean       # choosability, criticality, Gallai trees
│       │       ├── Lemmas.lean
│       │       └── README.md
│       └── Literature/
│           └── Coloring/
│               └── <Author_Result>/
│                   ├── Statements.lean   # typechecks; proofs may be sorry
│                   ├── Proofs.lean
│                   ├── status.toml       # machine-readable claim status
│                   └── Notes.md
│
├── empirical/                   # ── EMPIRICAL TIER (Python) ──
│   └── konigsberg_empirical/
│       ├── core/                # shared graph representation
│       ├── coloring/            # fixer_breaker, alon_tarsi, list checks
│       ├── search/              # nauty/geng enumeration, SAT/ILP
│       └── backends/            # optional external solvers
│
├── harness/                     # ── AGENT TIER (Python) — CORE ──
│   └── konigsberg_harness/
│       ├── agent.py             # the loop
│       ├── tools/registry.py    # tool registration + dispatch
│       ├── tools/lean_tools.py
│       ├── tools/empirical_tools.py
│       ├── tools/bridge.py      # empirical ↔ formal seam
│       ├── context/library_map.py  # ranked lemma surfacing
│       ├── lean_repl.py         # persistent Lean environment
│       ├── ledger.py            # epistemic status — the spine
│       ├── io.py
│       └── models.py            # provider routing
│
├── vendor/
│   └── choosability-oracle/     # Landon's .NET build — reference oracle for validating the Python port, then deleted
│
├── ci/
│   ├── check_axioms.py
│   ├── check_status.py
│   └── check_no_sorry.py
│
├── tests/
│   ├── differential/            # Python port vs .NET oracle
│   └── evals/                   # agent task benchmark suite
│
└── templates/
    ├── new-area/
    └── new-literature-entry/
```

**Guard rail:** Foundations creep is the top structural risk. If a definition is coloring-specific it goes in `Areas/Coloring`, never Foundations. If Foundations ends up 80% coloring machinery, this is a coloring tool wearing a general-purpose costume and no second area will ever fit.

---

## 5. The trust spine

The single most important subsystem. Everything else is replaceable; this is not.

### 5.1 `status.toml` schema

Every literature entry and every contributed lemma carries machine-readable status.

```toml
[entry]
name = "CranstonRabern_LineGraphBK"
citation = "..."
area = "coloring"

[[claims]]
lean_name = "Konigsberg.Literature.Coloring.CranstonRabern.line_graph_BK"
status = "stated"        # formalized | stated | informal
axioms = []              # populated by CI from #print axioms
verified_at = "<commit>"
```

Status meanings:
- **`formalized`** — proved in Lean, no `sorry`, axioms within whitelist.
- **`stated`** — statement typechecks; proof is `sorry`. **Still valuable**: usable as an explicit hypothesis, `decide`-checkable on small cases, and an open invitation for community contribution.
- **`informal`** — notes and reference only.

### 5.2 CI gates (non-negotiable)

| Gate | Enforces |
|---|---|
| `check_axioms.py` | `#print axioms` on every claim; reject anything beyond `propext`, `Classical.choice`, `Quot.sound` unless explicitly whitelisted |
| `check_no_sorry.py` | No `sorry`/`admit` in anything claiming `formalized` |
| `check_status.py` | `status.toml` matches reality — a `formalized` entry containing `sorry` fails the build |

`native_decide` is **not** whitelisted by default (it trusts the compiler). Whitelist per-case with written justification or not at all.

### 5.3 Runtime ledger

`ledger.py` enforces the same guarantee at agent runtime. Every agent-surfaced claim is tagged:

- `proved` — Lean, clean axioms
- `proved-mod-axioms` — Lean, non-standard axioms listed
- `stated` — Lean statement, unproved
- `solver-certified` — fixer-breaker / Alon–Tarsi certificate
- `python-checked` — empirical, up to stated bound
- `conjectured` — model output, unverified

**The agent must be structurally incapable of upgrading a status.** Not "instructed not to" — incapable, because the tag is attached by the tool result, not by the model.

**The hard trust boundary is the ledger.** Model prose is commentary. Final answers
are presented in two zones — `Established (ledger)` (rendered from Claims minted
this turn) and `Commentary` (the model's free text, marked unverified). Grounding
rules in the system prompt reduce fabricated verdicts when tools fail, but they
do not make free-text math claims mechanically checkable. Only Claims carry trust.

> The project's credibility dies permanently the first time it reports "proved" about something false. Merge-time honesty (CI) and runtime honesty (ledger) are the same guarantee enforced at two moments. Skip either and the corpus rots.

---

## 6. Formal tier

### Dependency model
mathlib4 is a **Lake dependency, never a fork**. Pinned by commit, `lake exe cache get` for prebuilt oleans (essential — the agent cannot wait hours per environment spin-up). `.lake/` is not committed. Fork only if upstreaming becomes necessary, which it should not early.

### What mathlib provides
`SimpleGraph`, adjacency, subgraphs, `SimpleGraph.Coloring`, `Colorable`, `chromaticNumber`, degree/`neighborFinset`, `Finset`/`Fintype` machinery, some clique material.

### What must be built
Substantially more than expected. Mathlib has **essentially no list-coloring theory**.

- `ListColoring`, `ListColorable`, choosability number
- `Critical`, `ListCritical` (vertex- and edge-)
- Low-degree vertices, average degree, `bad K₂` components, Gallai trees, degree-choosability
- The connecting lemmas that make paper theorems statable

### The definitional layer is the highest-leverage, least-automatable work
A wrong `ListCritical` definition makes true theorems unprovable or trivially false. **Do not delegate this.** It is a modeling problem, not a proof-search problem, and everything downstream inherits its quality.

### Lean tooling
Persistent environment via LeanREPL (not shell-outs per snippet) — keeps live state, returns structured goal state, acceptable latency.

---

## 7. Empirical tier

### The solver layer is the core oracle, not a support act

Reframed after feedback drawn from Tao's Equational Theories Project. ETP's lesson
was that cheap *complete* solvers (Vampire for entailment, finite model finding for
refutation) did the overwhelming bulk of the work; LLMs and humans handled only the
residue. Konigsberg's equivalent of Vampire is not a Lean tactic — it is this
empirical tier: SAT for k-/list-colorability, geng/nauty for generation, and
Rabern's choosability engine. So this tier is a **first-class oracle**, and the
WebGraphs reimplementation is core infrastructure, not a legacy port to scaffold
and abandon. (Deleting `vendor/` still happens — but it deletes only the .NET
*reference* implementation once the Python port is validated against it; the
*capability* is permanent.)

**Refutation before proof.** Most conjectures an agent generates in coloring die on
≤10 vertices. The empirical tier's first job is to kill them there, at near-zero
cost, before Lean or an LLM is ever invoked. Cheap refutation outweighs clever
proving. This should be a mandatory first gate on any generated conjecture, not an
optional tool.

**Completeness is uneven — keep the ledger honest about it.**
- SAT decides *k-colorability* and *L-colorability* (a single list assignment)
  exactly — NP problems a SAT solver eats. These scale refutation well past the
  brute-force ceiling and yield `python-checked` results up to the stated n.
- *k-choosability* is Π₂ (it quantifies over all list assignments). No single SAT
  call decides it; SAT only accelerates each inner instance, so the outer search
  is still search. The exhaustive checker is exact only for tiny graphs.
- *Alon–Tarsi* is a **sufficient** condition (AT number ≥ choice number): it can
  certify choosable, but a failure proves nothing. Its results are
  `solver-certified` / `certificate-checked`, never reported as a decided
  `python-checked` non-result.

### Landon Rabern's choosability engine

`WebGraphs` (C#/Silverlight) contains roughly a decade of specialized coloring-search code: **FixerBreaker** (fixer-breaker game solver for online/list choosability), **Polynomials** (Combinatorial Nullstellensatz / Alon–Tarsi), assignment enumerators, independence ratio, planar machinery, bit-level graph generation.

This is the empirical engine, already written. Silverlight is dead; the algorithms are not.

### Port strategy: oracle-guided reimplementation

1. Build the .NET compute libraries (Silverlight UI is discarded; .NET Core is cross-platform).
2. Place in `vendor/choosability-oracle/`, callable by subprocess.
3. Reimplement in Python under `empirical/konigsberg_empirical/coloring/`.
4. **Differential test**: feed nauty-generated graphs to both, assert identical output.
5. **Retirement bar**: agreement across all graphs up to n=10 plus a sampled set of larger ones.
6. Delete `vendor/`. Tests then pin against recorded oracle outputs.

This converts "did I port FixerBreaker correctly?" from a hope into a CI check. Critical, because a silent porting bug in Alon–Tarsi poisons every empirical result the agent reports.

### Other empirical capabilities
- `nauty`/`geng` enumeration with degree/connectivity constraints
- SAT/ILP for chromatic and list-chromatic queries beyond brute force
- Counterexample search: enumerate to a bound, test predicate, return first violation — **the highest-ROI tool in the system**, because it kills bad conjectures before formalization cost is incurred
- Optional Sage backend for standard queries

**Licensing:** resolved — Landon (a coauthor) has agreed to reuse of the ported
algorithms. M4 is no longer licensing-blocked. Note that the SAT layer is
licensing-independent regardless, and already delivers the complete decision core
for k-/L-colorability without any ported code.

---

## 8. Harness

### Reference architecture
Patterns drawn from **Aider** (Apache 2.0) and Anthropic's public engineering writing. **Not** from the leaked Claude Code source or clean-room rewrites derived from it — a tool whose entire value proposition is trustworthiness cannot have contaminated provenance.

| Concern | Source | Konigsberg |
|---|---|---|
| Core loop | both converge | while-loop + tool dispatch |
| Context surfacing | Aider's repo map | `library_map.py` |
| Sandboxing | agentic-coding practice | subprocess isolation + timeouts |
| Verification | evaluator-optimizer pattern | **deterministic** — Lean, not an LLM |
| Tool evals | Anthropic tooling guidance | `tests/evals/` from day one |

### Tool set

**Formal**
- `lean_check(snippet)` — typecheck against live environment; returns goal state + errors
- `lean_typecheck_statement(stmt)` — statement well-formedness without proof (catches "proved the wrong thing")
- `lean_eval(expr)` — `#eval`/`#reduce`, decidable computation inside Lean
- `lean_search(query)` — `exact?`/`apply?`/Loogle-style search over mathlib + own library
- `lean_add_to_library(...)` — gated commit of accepted lemmas

**Empirical**
- `counterexample_search(predicate, bound)`
- `fixer_breaker(graph, list_sizes)` — specialized, hard to reproduce, **the differentiator**
- `alon_tarsi(graph)`
- `graph_enumerate(n, constraints)`
- `sat_query(...)` / `ilp_query(...)`

**Bridge**
- `export_graph_to_lean(graph)` — Python graph → `SimpleGraph (Fin n)` for `decide`-based formal checking

### `library_map.py` — the key context borrow

The agent cannot fit mathlib + Foundations + Literature into context. Aider solves the analogous problem with a tree-sitter repo map: a ranked structural summary fitted to a token budget, selected by relevance to the current task, using graph ranking over the dependency graph.

Konigsberg's version ranks **lemmas and definitions by applicability to the current goal state** rather than source symbols by reference count. Same architecture, domain-swapped. This is the difference between an agent that reinvents `Finset` lemmas and one that uses the library it has.

### Deliberate non-borrowings
- **Edit formats / diff application** — irrelevant; the "edit" is a snippet that typechecks or doesn't
- **Filesystem access without sandbox** — inverted; every Lean elaboration and solver call is isolated and timed (`decide` on a large graph will hang)
- **Auto-commit everything** — library commits are gated behind the axiom check, never automatic

### Patterns to skip in v1
Parallelization, orchestrator-subagents, multi-agent architectures. A single loop over good tools first; complexity only when measurably justified.

---

## 9. Open source and governance

### Structure
- **Core** (harness, ledger, CI gates, Foundations API) — tightly controlled.
- **Periphery** (`Areas/*`, `Literature/*`) — community-contributable against fixed CI contracts.

### Contributor reality check
The contributor pool is {graph theorists} ∩ {people who write Lean}, which today is small. Lower the barrier deliberately:
- **Statement-only contributions are first-class.** A theorist who states their theorem in Lean with `sorry` has contributed real value.
- **Empirical contributions need no Lean fluency.**
- **Templates are the product** for community growth. Someone adds `Matching/` by copying `templates/new-area/`. If the template is good, contribution is mechanical; if absent, every new area is a bespoke negotiation and growth stalls.

### Licensing
Apache 2.0 (matches mathlib, frictionless). Landon has agreed to reuse of the
ported algorithms, so the license is unblocked.

### Strategic caution
"The community will build out other areas" is the standard open-source dream and usually does not happen unaided. **Architect so the project is fully valuable if it is only ever you**, and treat contributors as upside. The coloring vertical must stand alone as a useful instrument for your own BK work. If it does, contributors follow the utility. If it doesn't, no governance structure will summon them.

---

## 10. Milestones

| # | Deliverable | Proves |
|---|---|---|
| **M0** | Lake project + pinned mathlib + `lake exe cache get` working; `lean_check` round-trips | Environment is viable |
| **M1** | Axiom gate + `check_no_sorry` in CI; `ledger.py` skeleton | **Trust spine before anything else** |
| **M2** | Foundations + `Areas/Coloring/Basic.lean` — definitional layer, human-authored | The modeling is right |
| **M3** | Empirical tier: enumeration + counterexample search + **SAT decision layer** (k-/L-colorability) | Immediate standalone utility; the complete-solver refutation core |
| **M4** | Landon engine ported; differential tests green; `vendor/` deleted (licensing cleared) | The specialized choosability accelerator on top of SAT |
| **M5** | One anchor paper statement-formalized with `status.toml` | Literature-as-Lean concept end to end |
| **M6** | `lean_search` + `library_map` | Agent becomes competent rather than flailing |
| **M7** | Bridge + full agent loop with provenance tagging | It is a research assistant |
| **M8** | Attack one real open sub-lemma from BK-adjacent work | **The honest version of the north star** |

M1 before M2 is deliberate. Building the corpus before the gate means retrofitting trust onto content, which never fully works.

**Reprioritization (post-ETP feedback).** The solver/refutation layer is core, not
late. The SAT decision core (part of M3) and Rabern's engine (M4) are the oracle
that does the bulk of the work; proof (Lean) and generation (LLM) handle the
residue. Concretely: SAT k-/L-colorability landed with M3; M4 is unblocked
(licensing cleared) and bumped in priority; and refutation is a mandatory first
pass on any generated conjecture — kill it on ≤10 vertices before Lean or an LLM
sees it.

---

## 11. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Agent reports `sorry`-backed claim as proved | **Fatal** | Axiom gate + runtime ledger; status attached by tool, not model |
| Foundations creep → coloring tool in general-purpose costume | High | Hard review rule; second area attempted early as a stress test |
| Wrong definitional layer makes theorems unprovable | High | Human-owned, reviewed before any dependent work |
| Silent bug in ported solver | High | Differential testing against oracle before retirement |
| mathlib churn breaks the build | Medium | Pin by commit; deliberate bumps only |
| Autoformalization ambition consumes the project | Medium | Scoped as human-in-the-loop, statements-first |
| No contributors materialize | Medium | Build to be worth it solo |
| Provenance contamination from leaked source | High | Aider + public docs only; documented policy |

---

## 12. Open decisions

1. **LeanREPL vs. alternative Lean interaction layer** — evaluate current options before committing; this is a hard-to-change contract.
2. **Sage as a backend** — genuine dependency or avoid the weight? Affects install story.
3. **Anchor papers for `Literature/`** — pick 2–3 where you have the expertise to get statements right. Rabern list-critical / average-degree work and the line-graph BK result are the natural candidates.
4. **Landon's licensing terms** — RESOLVED. He has agreed to reuse; M4 unblocked.
5. **Model routing policy** — cheap models for empirical dispatch, frontier for proof search; thresholds TBD.

---

## 13. The one-paragraph version

Konigsberg is a monorepo with a Lean formal tier (mathlib as a dependency, a hand-built choosability/criticality library, and a corpus of formalized literature statements), a Python empirical tier (enumeration, SAT, and a reimplementation of Landon Rabern's choosability solvers validated by differential testing against the original), and an agent harness that orchestrates both behind a rigid epistemic ledger. Graph coloring is built out first as the exemplar area and as the template other areas copy. The north star is materially accelerating a human attack on Borodin–Kostochka; the deliverable at every milestone is an instrument that is useful on its own terms.
