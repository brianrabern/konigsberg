# Konigsberg

*Formal and empirical tools for graph theory research.*

An agentic research assistant for graph theory. The LLM is the reasoning core;
the value is the **harness**: deterministic tooling, a formally verified library,
and an epistemic ledger that makes every claim traceable to *how* it was
established.

Konigsberg is a monorepo with a Lean formal tier (mathlib as a dependency, a
hand-built choosability/criticality library, and a corpus of formalized
literature statements), a Python empirical tier (enumeration, SAT, and a
reimplementation of Landon Rabern's choosability solvers validated by
differential testing against the original), and an agent harness that
orchestrates both behind a rigid epistemic ledger. Graph coloring is built out
first as the exemplar area and as the template other areas copy. The north star
is materially accelerating a human attack on Borodin–Kostochka; the deliverable
at every milestone is an instrument useful on its own terms.

## Layout

| Path | Tier | Owner |
|---|---|---|
| `formal/` | Formal (Lean): mathlib + own library + formalized literature | core (`Foundations/`), community (`Areas/`, `Literature/`) |
| `empirical/` | Empirical (Python): enumeration, SAT, choosability solvers | core + community |
| `harness/` | Agent (Python): loop, tools, ledger, context surfacing | core |
| `ci/` | Trust gates: axioms, sorry, imports, conventions, audit self-test | core |
| `vendor/` | Landon Rabern's .NET oracle — TEST ORACLE ONLY, to be deleted | — |
| `templates/` | Copyable skeletons for new areas / literature entries | — |

Lean and Python never import each other. The harness is the only thing that
talks to both, via subprocess.

## Claim status — a structured record, not a rank

A claim's trust is a `Provenance` record (`harness/konigsberg_harness/ledger.py`)
carrying an explicit **trust root**, not a point on a line. `proved` (Lean
kernel) and `solver-certified` (empirical) bottom out in different things; the
ledger keeps that distinction visible rather than collapsing it into an ordinal.

**Konigsberg's hard trust boundary is the ledger.** Everything the model says in
prose is commentary and must be read as such. Final answers are rendered in
zones — `Established (ledger)` (generated from Claims, not model text), optional
`Definition used:` (which convention drove the verdict), optional
`References (corpus)`, and `Commentary` (unverified prose). System-prompt rules
reduce the chance of misleading narration, but they are not a kernel-style
guarantee: only Claims carry trust.

**Definitional fidelity is upstream of the ledger.** The ledger certifies that
claims are *true*, not that they *answer the question asked*. If the agent
interprets "4-list-critical" as "4-choosable" and then correctly proves
4-choosability, the trust gates pass — they certify truth, not relevance. Tools
that bake in an index (`list_critical`) and a visible `Definition used:` line
remove the common failure mode and make the interpretation falsifiable, but
they cannot fully guarantee correct interpretation. That residual gap — "did
you prove the right theorem?" — is inherent to the trust model and should stay
named, not hidden. For the formal tier the same ceiling is spelled out in
[`docs/TRUST.md`](docs/TRUST.md): kernel + axiom gates guarantee *proofs*;
statements get sanity checks and a best-effort read, with no warrant that they
say what the docstring claims.

| Human label | Trust root | Means |
|---|---|---|
| `proved` | Lean kernel | No `sorry`; axioms within whitelist |
| `proved-mod-axioms` | Lean kernel | Proved; non-standard axioms listed |
| `certificate-checked` | re-checked certificate | Solver emitted a finite object we independently verified |
| `solver-certified` | solver + validated port | Solver asserted; port matches oracle. **Not** re-checked |
| `python-checked` | enumeration | Empirical, up to a stated bound |
| `stated` | — | Statement typechecks. Says nothing about truth |
| `conjectured` | model | Unverified LLM output |

## Run the Borodin–Kostochka hunt on a local LLM

Clone-to-campaign walkthrough (llama.cpp / Qwen, no cloud key), including
Lean/mathlib setup, `.env`, a 20-round smoke, and an unattended `--forever`
soak: **[`docs/LOCAL_BK_HUNT.md`](docs/LOCAL_BK_HUNT.md)**.

## Quickstart

Prereqs: [`elan`](https://github.com/leanprover/elan) (Lean toolchain manager),
Python ≥ 3.11, and [`uv`](https://docs.astral.sh/uv/). On macOS, [`Homebrew`](https://brew.sh)
is used to install nauty when missing.

```bash
# Formal tier — M0: get mathlib, verify the environment round-trips
cd formal
lake update                 # freezes the real mathlib commit into lake-manifest.json — COMMIT IT
lake exe cache get          # prebuilt oleans; do NOT build mathlib from source
lake build

# Python + system deps (uv sync + nauty/geng via brew/apt when missing)
cd ..
make deps                   # or: uv run python scripts/ensure_deps.py --yes

# Interactive session (Claude-Code-shaped REPL; ledger persists under ~/.konigsberg/sessions/)
uv run konig                         # short alias
uv run konigsberg                    # same
uv run konig --task "…"              # headless one-shot
uv run konig --until-proved --task "Prove …"   # autonomous hunt until lean_prove
uv run konig --forever                         # BK campaign: until proved/disproved
uv run konig --continue              # resume latest session
# Live model: Anthropic (ANTHROPIC_API_KEY) or local llama.cpp
# (KONIGSBERG_PROVIDER=local + OPENAI_BASE_URL). Repo-root `.env` is auto-loaded;
# scripted fake otherwise. Chat model: ANTHROPIC_MODEL=opus 4.8, or
# KONIGSBERG_MODEL=<gguf-name> locally (or /model in-session).
# Local BK hunt (clone → llama-server → --forever): docs/LOCAL_BK_HUNT.md
# Hunt + locked lemmas: see docs/handoff/HUNT_AND_LEMMAS.md.

# Trust gates (run what CI runs)
make gates
# equivalent:
#   uv run python ci/self_test_audit.py
#   uv run python ci/referee_self_test.py
#   uv run python ci/reduction_self_test.py
#   uv run python ci/discharging_self_test.py
#   uv run python ci/check_status.py formal
#   uv run python ci/check_no_sorry.py formal
#   uv run python ci/check_axioms.py formal
#   uv run python ci/check_imports.py formal
#   uv run python ci/check_conventions.py formal
```

## Status

Working three-tier instrument (Lean library + empirical solvers + ledger-backed
harness). `--forever` is the Borodin–Kostochka campaign: it runs until a durable
kernel `lean_prove` of `borodinKostochka` lands, a certified Δ ≥ 9 counterexample
lands, or you stop it. Model prose never counts. See
[`docs/LOCAL_BK_HUNT.md`](docs/LOCAL_BK_HUNT.md) to clone and hunt on a local
LLM. `PLAN.md` tracks remaining milestones; “Scaffold” is no longer the state
of the tree.

**What to read:** hunt = `docs/LOCAL_BK_HUNT.md`; trust = `docs/TRUST.md`.
`docs/handoff/` is a lab notebook — ignore it unless you are debugging a
specific ingest. `vendor/` is a **test oracle** for differential tests; do
not build it to run the hunt (those tests skip if the oracle is missing).

## License

Source-available for private research. **Not Apache 2.0 yet** — reuse terms
for the Rabern choosability port must be resolved in writing before a public
OSI release. See `LICENSE`.
