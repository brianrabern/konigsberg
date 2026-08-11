# Fidelity gates — mechanize the statement check (Cursor spec)

*We just hand-verified 13 stated theorems and caught two bugs by eye (a false
`HajnalLemma`, a weakened `TransitiveClusteringBigCliques`). That doesn't scale and
it isn't repeatable. `geoconuk/lean-misc-math` (a sibling project: Claude-generated
Lean on Mathlib, human-curated) has already built the machinery to make this check
mechanical. Adopt it. The kernel guarantees proofs; nothing yet guards our
**statements** — and for a statements-first corpus where proofs are `sorry`, the
statement is the entire deliverable.*

Konigsberg currently has **none** of these: `autoImplicit` is unset (defaults true),
0 of 18 Literature entries ship sanity checks, there is no audit self-test, and no
import-coverage guard.

---

## WP1 — Sanity checks in every entry (the important one)

The largest failure mode for machine/agent-generated statements is a theorem that is
proved (or `sorry`'d) but **doesn't say what it claims** — vacuous hypotheses, wrong
quantifier, junk-value convention (`x/0=0`, truncated `ℕ` subtraction), or a bespoke
definition standing in for the intended one. The defense is a concrete witness,
checked in the build, **independent of the proof**.

Every Literature entry (stated *and* formalized) ships, in a build-checked
`SanityChecks.lean` (imported like the rest):

1. **Non-vacuity witness.** An `example` that instantiates the theorem's hypotheses
   at a concrete small structure and *discharges them* (by `decide`/`norm_num`),
   proving the hypotheses are simultaneously satisfiable. A theorem whose hypotheses
   can't be met is vacuously true and worthless — this rules that out.
2. **Concrete conclusion check.** An `example` asserting the *conclusion*, at the
   same concrete instance, holds by `decide`/`norm_num` — **without invoking the
   theorem** (which may be `sorry`). This is an independent probe that the statement
   is true where it's cheap to check.

Both must use `decide`/`norm_num` on *tiny* instances (small `SimpleGraph (Fin n)`
with decidable `Adj`, as `verify_coloring` already does; a concrete `MvPolynomial`
for the Nullstellensatz group). `native_decide` stays banned — `decide` yields a
kernel proof with whitelist axioms.

Why this matters here specifically:

- **Our proofs are `sorry`.** For a stated target the sanity `example`s are the
  *only* independent evidence the statement isn't garbage. A vacuous stated theorem
  is a phantom target that looks like real work.
- **It would have caught `HajnalLemma`.** A conclusion check on `K₃` with `𝒬 = ∅`
  fails (`0 + 3 ≥ 6` is false); with `𝒬 = {univ}` it passes — surfacing that the
  statement's truth turns on nonemptiness, mechanically, instead of by my reading.

Backfill all 18 existing entries; require it for every new one.

## WP2 — `autoImplicit false` (one line, real footgun)

Set `autoImplicit false` (and `relaxedAutoImplicit false`) globally in
`lakefile.toml`. It stops a mistyped identifier from silently becoming a fresh
∀-quantified variable that quietly changes a statement — a pure fidelity hazard,
currently wide open. Rebuild; fix any fallout (add explicit `variable`/binders where
a genuine implicit was relied on).

## WP3 — Audit self-test (prove the gate isn't a no-op)

Add `ci/self_test_audit.py` (or `scripts/self-test-audit.sh`): generate a throwaway
declaration containing (a) a `sorry`, (b) a locally-declared `axiom`, and (c) a
`native_decide` use; run `check_no_sorry` / `check_axioms` against each and **assert
each is rejected (non-zero exit)**. Fail CI if any slips through. "An audit that
passes everything is worse than none" — and we've hit exactly this class before (the
LeanREPL env-threading bug that would have reported "no axioms" for anything). Wire
it into the CI job ahead of the real audit.

## WP4 — Import-coverage check

Add `ci/check_imports.py`: assert every `formal/Konigsberg/**/*.lean` result file is
reachable from the root import (`Konigsberg.lean`), so no entry can dodge
`check_axioms`/`check_no_sorry` by being unreferenced. Fail loudly on an orphan file.

## WP5 — Standardize the entry template + honest-boundary doc

- **Template.** Extend `Notes.md` to the fixed shape (mirroring lean-misc-math's
  30-second-review layout): `## Informal statement` (English claim), `## Source`
  (book §/citation), `## Provenance` (what was agent-generated vs. hand-checked),
  `## Fidelity review` (already present — keep), and a pointer to `SanityChecks.lean`.
  A convention check (`ci/check_conventions.py`) fails any entry missing an informal
  statement, source, or sanity checks.
- **Honest-boundary doc.** A short `docs/TRUST.md` (or PLAN section) stating the
  boundary plainly, in lean-misc-math's spirit and matching what this project already
  learned: the kernel + axiom gate guarantee **proofs**; **statements** get a
  best-effort read plus sanity checks and carry no warrant that they say what the
  docstring claims. "A mistake here is not a wrong proof — it's a statement that
  doesn't say what it appears to." This is the definitional-fidelity ceiling, stated
  once, honestly.

---

## Acceptance

- Every Literature entry ships build-checked non-vacuity + conclusion sanity
  `example`s (18 backfilled; required for new entries via the convention check).
- `autoImplicit false` set globally; build green.
- CI runs the audit self-test (planted `sorry`/axiom/`native_decide` all rejected)
  and the import-coverage check; both fail loudly on violation.
- `Notes.md` template enforced; `docs/TRUST.md` states the statement/proof boundary.
- `ruff`/`pytest` green; existing axiom gates unchanged in behavior.

## Scope discipline

- Sanity checks are *tiny* `decide`/`norm_num` probes — not proofs, not exhaustive.
  Their job is to catch vacuity and gross statement drift cheaply, not to verify the
  theorem. Keep instances small so the build stays fast.
- Don't weaken any existing gate; these are additive guards around statements, the
  layer the kernel can't reach.
- These gates harden the *formal tier*; they don't touch the ledger/trust roots in
  the empirical/agent tiers (those are already sound).
