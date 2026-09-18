# Durability pass — make proofs stick (Cursor spec)

*Konigsberg can prove BK-surface lemmas with clean kernel axioms, but nothing it proves
survives the session. It's a prover with amnesia: every result lives in an ephemeral,
un-retractable Lean env, disconnected from the durable corpus. The bridge lemma was
proved twice from cold and is still `stated` in source. Fix retention before adding more
math — once proofs bank, the reducibility engine's forbidden-configs become a number that
goes up instead of a thing we re-litigate each session.*

The root cause is **not** a missing write-back. `lean_add_to_library`
(`tools/library_writeback.py`) is built, robust, and fail-closed. The problem is deeper
and is WP1.

---

## WP1 — Close the session-env ↔ corpus gap (the real blocker)

**The bug.** Proofs are built as a *chain* of separate `lean_prove` calls — each helper
lemma (`Konigsberg.BKBridge.induce_compl_ne_top`, `…colorable_induce_of_subgraph_coe'`,
`…fChoosableZ_mono`, …) is minted into the **persistent session env**. But
`lean_add_to_library` takes a **single `snippet`** and re-elaborates it against
`import Mathlib` + `import Konigsberg` — i.e. the **committed corpus**, *not* the session
env (`library_writeback._statements_lean`, and the live re-elaborate at
`repl.send(snippet)` in `lean_add_to_library`). So a target theorem whose proof body
refers to `BKBridge.*` names **cannot be promoted**: those names don't exist in a fresh
corpus build, the snippet won't elaborate, write-back refuses. The session env and the
durable corpus are two different worlds and nothing carries a multi-declaration proof
across. That is why value gets trapped.

**The fix: make "proved" and "promotable" coincide.** A proof is only durable if it is a
single **self-contained snippet** — all helper lemmas + the target, one namespace — that
elaborates against a **fresh corpus env** (Mathlib + committed Konigsberg only, no session
decls). Give the harness a way to *know* a proof is that, and steer the producer to build
that shape.

Concretely:

1. **`lean_prove` gains a `durable: bool = False` mode.** When `durable=True`, elaborate
   the snippet in a **fresh child env** seeded only from the committed corpus preamble
   (`import Mathlib` + `import Konigsberg`), *not* the accumulated session env. Success
   ⇒ the snippet is self-contained and promotable; the minted `proved` Claim records
   `durable=True`. A proof that passes ordinary `lean_prove` but *fails* `durable` is
   exactly one leaning on ephemeral session decls — surface that distinction in the Claim
   and in `/tools` output so it's visible, not silent.

2. **`lean_add_to_library` requires `durable=True` provenance.** Promotion already
   re-elaborates against the corpus; make it refuse a Claim not minted in durable mode,
   with a message that says *why* ("proof depends on session-only declarations; assemble a
   single self-contained snippet"). No more discovering non-promotability at the write
   boundary.

3. **`lean_export_chain(target_name)` helper (optional but high-value).** Emit the
   transitive closure of *session-authored* dependencies of `target_name`, topologically
   ordered, as one snippet in a target namespace — turning a scattered `BKBridge.*` chain
   into a promotable block automatically. If this is too much for v1, skip it and rely on
   the producer building self-contained snippets, but the `durable` check (1) is
   non-negotiable — it's what makes the discipline enforceable instead of hoped-for.

Mission/prompt note: teach the producer that the *unit of durable work is a
self-contained snippet*, not a pile of env lemmas. Prove helpers inline (or in the same
namespace) and validate the whole thing with `durable=True` before considering it done.

## WP2 — Env hygiene: retract + transactional `lean_prove`

The env accumulates declarations and **cannot retract** — a failed submission left a
`sorryAx`-poisoned `colorable_induce_of_subgraph_coe` stub that forced a primed-name
workaround. Two fixes:

1. **Transactional `lean_prove`.** Elaborate in a scratch/child env; **commit to the
   session env only on full success**. A failed or partial elaboration must leave **no**
   declaration behind. This alone kills the poisoned-stub class.

2. **`reset_env` and `retract(name)` tools.** `reset_env` returns the session to the clean
   corpus preamble (drop all session decls); `retract(name)` drops a single named decl.
   Both let the agent recover from a degraded env instead of working around it with primed
   names. Wire `reset_env` into `/reset` in the REPL.

## WP3 — Referee empty-output (why `/promote` couldn't vet)

The `/promote` you ran blocked with *"adversarial referee returned empty output"* — that's
`_referee_agent_pass` in `referee.py` raising `RefereeUnavailable` because the referee
`Agent` (`max_steps=8`) produced empty `commentary/final`. The referee didn't error; it
**ran out of steps on tool calls and never emitted its final JSON**. Fix:

1. **Force a final report turn.** After the agent loop (or on step-exhaustion), issue one
   final **no-tools** turn instructing the referee to emit *only* the JSON report from what
   it has gathered. Only if *that* is empty/invalid is it truly `unavailable`.
2. **Distinguish exhaustion from error** in the `unavailable` reason string
   ("referee exhausted steps before emitting report" vs "model error: …") so the failure
   mode is diagnosable rather than a generic empty.
3. Modestly raise `max_steps` (8 → ~12) and keep fail-closed throughout: a referee that
   still can't produce a report blocks promotion, never accepts.

## WP4 — Check-depth: stop the vacuity/faithfulness false-passes

On the bridge Claim the heuristic checks no-opped on exactly the features they exist to
test (`referee.py`): `vacuity_triviality` **passed** a `⇒ False` claim whose key
hypothesis (`KCritical G D`) has no exhibited witness; `definition_predicate_faithfulness`
returned `na` though the claim rests on `KCritical`/`FChoosableZ`. Cause: the checks regex
the thin `claim.statement` *string* instead of the Lean **type + dependencies**.

1. **Vacuity must fire on `⇒ False` (and unit-concluding) claims.** `_VACUOUS_PATTERNS`
   matches `False\s*→` but not a `→ False` **conclusion**. Any claim whose conclusion is
   `False` (a minimal-counterexample lemma) is worthless if its hypotheses are jointly
   unsatisfiable, so it must **fail/block unless a satisfiability witness for the
   load-bearing hypothesis is present** (a `SanityChecks` instance, or a passing tool
   probe). Heuristic can't prove satisfiability ⇒ its honest verdict is *block*, not
   *pass*.
2. **Faithfulness/hypothesis checks read the Lean statement, not the claim string.** When
   a `repl` is available, pull the actual type (`#check`) and the dependency constants
   (`#print axioms` / the decl's used-constants) and test *those* for bespoke,
   corpus-authored notions and for a parseable binder chain — including `∀ … → … → False`.
   Regex over `claim.statement` is a fallback, not the primary path.
3. **Self-test fixture.** Add a planted `⇒ False`-with-unwitnessed-hypothesis claim to
   `ci/referee_self_test.py` and assert the referee **rejects/blocks** it. This exact shape
   is now a known blind spot; make it a regression.

---

## Acceptance

- `lean_prove(durable=True)` elaborates against a fresh corpus env; the minted Claim
  records durability; `lean_add_to_library` refuses non-durable Claims with a clear reason.
- `lean_prove` is transactional (failed elaboration leaves no decl); `reset_env` /
  `retract` exist and `/reset` is wired.
- `/promote` on a real, durable, referee-accepted claim runs the adversarial pass to a
  final JSON report (no spurious empty-output `unavailable`); genuine failures still block.
- `vacuity_triviality` blocks a `⇒ False` claim lacking a satisfiability witness;
  faithfulness/hypothesis checks consult the Lean type when a `repl` is present;
  `referee_self_test` covers the `⇒ False` fixture and is green.
- `ruff`/`pytest` green; existing fail-closed guarantees unchanged.

## Scope discipline

- Fail-closed stays absolute: every new failure path **blocks** promotion, never accepts.
- `durable` mode is the load-bearing idea; if `lean_export_chain` (WP1.3) is cut for v1,
  the `durable` check and the producer discipline must stay.
- Don't weaken any existing gate in `library_writeback.py`; these are additive.
- This pass buys *retention and a working promote*, not new mathematics — but it's the
  precondition for the reducibility engine to accumulate anything at all.
