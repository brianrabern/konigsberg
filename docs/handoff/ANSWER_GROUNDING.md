# Answer grounding + the pysat gap (Cursor spec)

*A live REPL run exposed two problems. One is boring (a missing runtime
dependency). The other is central: when `choosability_refute` failed, the model
fabricated a verdict — "C₅ is not 2-choosable" plus an unverified, incoherent "bad
list assignment" — in its final prose. The ledger stayed clean (that assertion
minted nothing), but the chat asserted an unbacked mathematical claim as if it
were a result, and was accidentally correct, which is worse. Konigsberg's hard
trust boundary is the ledger; this spec makes the prose layer stop pretending to
be one too.*

The transcript, for reference:
```
→ choosability_refute({'graph6':'Dhc','k':2})  ← [ERR] No module named 'pysat'
→ verify_coloring(...)                          ← [proved] (correct)
[final prose]: "No, C₅ is not 2-choosable. Bad list assignment: … wait, let me
recalculate …"   ← no certificate, never re-checked, minted nothing
```

---

## WP1 — `pysat` is a hard runtime dependency (trivial, do first)

`choosability_refute`, the CEGAR engine, and the BK-attack module all import
`pysat`. It works in the dev/test env but **`uv run konigsberg` does not have it**,
so the entire SAT/CEGAR empirical tier is dead in the actual product.

- Move `python-sat` from any optional extra into the harness's **core runtime
  dependencies** so the `konigsberg` entry point always has it.
- Add a fast import-time / startup check (or a test) asserting `pysat` is
  importable in the same environment the REPL runs in.
- **Missing-dependency failures must be loud, not swallowed.** A tool that fails
  because a dependency is absent should surface as a prominent REPL banner
  ("TOOL UNAVAILABLE: choosability_refute — pysat not installed"), distinct from
  an ordinary tool result, so neither the user nor the model can glide past it.

---

## WP2 — Answer-grounding discipline (the important one)

The ledger is mechanically honest; the model's natural-language answer is not. We
cannot make prose-grounding a kernel-style guarantee (detecting "did the model
assert an unverified theorem" in free text isn't mechanical). So this is a
two-part guard — a behavioral rule and a presentation separation — plus honest
docs about the residual softness.

### 2a. System-prompt rule (behavioral)

Add to the agent's system prompt, stated as a hard rule:

- **Do not state mathematical verdicts in the final answer unless backed by a
  ledger claim.** Every conclusion in the answer must trace to a Claim the tools
  minted this session.
- **If a tool fails or is unavailable, the result is "not established."** Report
  the failure plainly (which tool, why). Do NOT reconstruct the answer from prior
  knowledge, and do NOT substitute a memorized result for a tool result.
- **Never exhibit a certificate the tools did not produce and re-check.** No
  hand-written "bad list assignments," colorings, orientations, or proofs in
  prose. A certificate is only real if a tool minted it (e.g. a bad list from
  `choosability_refute`, a coloring re-checked by `verify_coloring`).
- **Distinguish established from conjectural.** The model may offer intuition or
  next steps, but must label them as commentary, not results.

### 2b. Presentation separation (structural)

The final render must make ledger-backed results and model narration visually
unequal, so confident prose can't masquerade as a result:

- Render the answer in two zones:
  - **`Established (ledger):`** — the claims minted this turn, each with its trust
    root (`proved` / `certificate-checked` / `solver-certified` / … ). This is
    generated from the `Ledger`, not from model text.
  - **`Commentary:`** — the model's free-text answer, clearly marked as
    unverified.
- If the ledger is empty for the question asked (as in the C₅ run — the refutation
  tool failed), the `Established` zone says so explicitly ("nothing established for
  this question; `choosability_refute` failed"), and the commentary cannot claim
  otherwise without contradicting the zone directly above it.
- `/ledger` remains the single source of truth; the `Established` zone is just its
  per-turn view.

### 2c. Honest docs (state the boundary)

In the README / PLAN trust section, state plainly: **Konigsberg's hard trust
boundary is the ledger. Everything the model says in prose is commentary and must
be read as such.** 2a/2b reduce the chance of misleading prose but do not make it
impossible — only the ledger carries trust. Do not oversell the prose guard as a
guarantee.

---

## Tests

- **WP1:** a test asserting `pysat` imports in the runtime env; a REPL/registry
  test that a dependency-missing tool failure renders as the loud "UNAVAILABLE"
  banner, not a plain result line.
- **WP2 (the load-bearing one):** drive the loop with a scripted model where a
  tool **errors** and the model's final turn nonetheless asserts a verdict. Assert
  that (i) the ledger is empty / contains no claim for that verdict, and (ii) the
  rendered answer's `Established` zone reports "not established" for it. This is
  the C₅ failure, encoded so it can't silently regress.
- Existing trust-invariant tests (`test_lying_final_mints_nothing`, trust-root
  stamping) must still pass — 2a/2b are additive.

---

## Acceptance

- `uv run konigsberg` has `pysat`; `choosability_refute` runs; missing-dep
  failures are loud.
- The agent's final answer is rendered in `Established (ledger)` vs `Commentary`
  zones; the Established zone is generated from the ledger, not model text.
- On a failed/again-unavailable tool, the agent reports "not established" and does
  not fabricate a verdict or certificate (system-prompt rule + regression test).
- Docs state the ledger-is-the-boundary position honestly.
- `ruff` clean, `uv run pytest` green.

## Scope discipline

- Don't try to *mechanically verify* free-text math claims — that's not the goal
  and isn't feasible. The goal is: back real results with the ledger, separate
  commentary visually, and never fabricate certificates.
- No change to how Claims are minted or to trust roots — this is about the answer
  surface, not the trust core.
- Keep the two-zone render simple text; no TUI.
