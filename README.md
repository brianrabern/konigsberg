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
uv run konigsberg                    # interactive
uv run konigsberg --task "…"         # headless one-shot
uv run konigsberg --continue         # resume latest session
# Real model when ANTHROPIC_API_KEY is set; scripted fake otherwise.

# Trust gates (run what CI runs)
make gates
# equivalent:
#   python ci/self_test_audit.py
#   python ci/check_status.py formal
#   python ci/check_no_sorry.py formal
#   python ci/check_axioms.py formal
#   python ci/check_imports.py formal
#   python ci/check_conventions.py formal
```

## Status

Scaffold. See `PLAN.md`-tracked milestones. The trust spine (`ci/`, `ledger.py`)
is built before corpus content by design — retrofitting trust onto content never
fully works.

## License

Apache 2.0, pending resolution of reuse terms for ported oracle algorithms.
See `LICENSE`.
