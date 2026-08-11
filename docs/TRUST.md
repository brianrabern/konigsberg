# Trust boundary — what Konigsberg guarantees

This is the honest ceiling for the **formal** tier.

## Guaranteed (mechanically)

| Gate | Rules out |
| --- | --- |
| `lake build` | Incorrect *proofs* — the kernel accepts nothing else |
| `ci/check_axioms.py` (+ `--run-lean` in CI) | `sorryAx`, local `axiom`s, `native_decide` (`Lean.ofReduceBool`) on claims marked `formalized` |
| `ci/check_no_sorry.py` | Token `sorry`/`admit` in `Proofs.lean` of formalized entries |
| `autoImplicit false` | Mistyped identifiers silently becoming fresh ∀-variables |
| `SanityChecks.lean` | Vacuous hypothesis packages and gross conclusion drift on tiny instances (`decide`/`norm_num` only) |
| `ci/check_imports.py` | Orphan `.lean` files that dodge the gates by not being imported |
| `ci/self_test_audit.py` | Gates that silently accept everything |
| `ci/check_conventions.py` | Literature entries missing Notes sections or SanityChecks |

## Not guaranteed

**That a statement means what its docstring / Notes claim.** That is the real
risk, and it is not fully automatable. A theorem can be kernel-correct (or
honestly `sorry`'d as `stated`), non-vacuous under sanity checks, axiom-clean
when formalized, and still not be the theorem you wanted — wrong quantifier,
truncated `Nat` subtraction, junk-value conventions, or a bespoke definition
standing in for the intended one.

A mistake here is **not a wrong proof**. It is a **statement that does not say
what it appears to**. Sanity checks and a best-effort fidelity read shrink that
space; they do not close it. Before depending on a Literature claim, compare
`## Informal statement` in `Notes.md` to the Lean statement and glance at
`SanityChecks.lean`.

## Scope

These gates harden the formal tier only. Empirical and agent tiers have their
own ledger / grounding trust roots; this document does not redefine those.
