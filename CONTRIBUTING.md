# Contributing to Konigsberg

The contributor pool is {graph theorists} ∩ {people who write Lean}, which today
is small. The barrier is lowered deliberately. You do **not** need to write
proofs, and you do **not** need Lean fluency for empirical work.

## Ways to contribute, from lowest to highest barrier

1. **Empirical (no Lean).** Solvers, enumerators, counterexample predicates, and
   tests under `empirical/`. Pure Python.
2. **Statement-only formalization (first-class).** State a theorem in Lean with
   `sorry` for the proof. A typechecking statement with `status = "stated"` is
   real, merged value: it is usable as an explicit hypothesis, `decide`-checkable
   on small cases, and an open invitation for someone to fill the proof.
3. **Proofs.** Discharge a `sorry` in an existing `stated` entry.
4. **New areas.** Copy `templates/new-area/`. If the template does its job,
   adding `Matching/` is mechanical.

## Core vs periphery

- **Core** (`harness/`, `ci/`, `formal/Konigsberg/Foundations/`) is tightly
  controlled and human-owned. Changes here are reviewed hard.
- **Periphery** (`formal/Konigsberg/Areas/*`, `formal/Konigsberg/Literature/*`,
  `empirical/`) is community-contributable against fixed CI contracts.

## The Foundations guard rail (read this before touching `Foundations/`)

If a definition is coloring-specific it goes in `Areas/Coloring`, **never**
`Foundations`. Foundations is area-agnostic. If Foundations fills with coloring
machinery, this becomes a coloring tool wearing a general-purpose costume and no
second area will ever fit. PRs that put area-specific defs in Foundations are
rejected on sight.

## The trust contract (non-negotiable)

Every literature entry and contributed lemma carries a `status.toml`. CI enforces:

- `check_no_sorry.py` — nothing marked `formalized` may contain `sorry`/`admit`.
- `check_axioms.py` — axioms must fall within the whitelist (`propext`,
  `Classical.choice`, `Quot.sound`) unless explicitly justified in writing.
  `native_decide` is **not** whitelisted (it trusts the compiler).
- `check_status.py` — `status.toml` must match reality.

Never report a claim at a status its evidence does not support. The project's
credibility dies permanently the first time it reports "proved" about something
false.

## Provenance

Harness design draws only from Aider (Apache 2.0) and public documentation. Do
**not** submit code derived — directly or via clean-room rewrite — from leaked or
reverse-engineered agent source. A tool whose entire value proposition is
trustworthiness cannot have contaminated provenance. By opening a PR you attest
your contribution is free of such provenance.

## Definitional review

Definitions (`Basic.lean`, `Foundations/`) are a modeling problem, not a
proof-search problem, and everything downstream inherits their quality. A wrong
`ListCritical` makes true theorems unprovable or trivially false. Definitional
PRs get human review before any dependent work is accepted.
