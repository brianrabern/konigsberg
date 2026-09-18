# The full Rabern method — reducible seeds + discharging (Cursor spec)

*Rabern's BK method is **reducibility + discharging**. The corpus and Hunt encode only the
reducibility half, so accumulating forbidden configurations never composes into a proof.
This spec adds (A) Rabern's known forbidden configurations as hunt seeds, (B) the
**discharging engine** — the missing half — that verifies a set of forbidden
configurations is **unavoidable** in a minimal counterexample, and (C) the bridge lemma
that closes reducible + unavoidable ⇒ no counterexample. The whole thing is made
tool-checkable by one fact: at the live regime **Δ = 9**, a critical counterexample has
every vertex of degree 8 or 9, so its local structure is finite and enumerable.*

Reducibility answers "which local configurations can't appear." Discharging answers "must
one of them appear." Only both together prove BK.

---

## Part A — Rabern's forbidden-configuration seeds (Tier 1 of RABERN_BK_INGEST)

Stop the hunt rediscovering C₄ from zero: pre-load Rabern's proven reducible joins as
seed cores.

`empirical/konigsberg_empirical/reduction/reducible_seeds.toml`:

```toml
# Each seed is a configuration Rabern/Cranston–Rabern proved reducible (f-choosable
# join, f(v)=d(v)-1). The engine re-derives reducibility; the seed just supplies the
# core + degree spec so the hunt starts from the known catalogue, not from zero.
[[seed]]
name      = "CR_dminus1_edge"        # human label
source    = "Cranston–Rabern, Coloring a graph with Δ−1 colors (1203.5380)"
core      = "A_"                     # graph6 of the core K
degrees   = [8, 8]                   # ambient degree spec d_G per core vertex (Δ=9 regime)
note      = "…which lemma / figure it comes from"
```

Populate from **"Coloring a graph with Δ−1 colors"** (1203.5380 min-counterexample study)
and **claw-free BK** (SIAM 2013, Tier 2 of the ingest). `campaign.py` reads this at
startup; the staircase's rung 2 becomes: *re-derive the next un-minted Rabern seed via
`reducible_configuration`, then extend past the catalogue.* `next_step` should cite the
next seed not yet on the ledger before inviting a novel core. Wire `format_campaign_snapshot`
to show `seeds: k/N re-derived`.

This is worthless without Part B — a bigger pile of forbidden configs is still just a pile.

---

## Part B — The discharging engine (the missing half)

### B0. The finiteness that makes it tractable

A minimal BK counterexample at Δ = D is `D`-critical ⇒ `δ ≥ D−1`, and `Δ = D`, so **every
vertex has degree `D−1` or `D`**. At **D = 9** that is degree 8 or 9 — a bounded, finite
local world. Bounded-radius neighborhoods are a finite, `geng`-enumerable set. Discharging
over them is therefore a finite computation the harness can check. **v1 targets D = 9**
(the crux case; Reed settles large D). General D is a symbolic argument — v2, out of scope.

### B1. Data model — `konigsberg_empirical/discharging/`

```python
@dataclass(frozen=True)
class Charge:
    """Initial charge μ(v) as a function of the vertex's degree.
    e.g. mu = {8: -1, 9: +1} (low vertices deficient, high vertices surplus)."""
    mu: dict[int, int]                 # degree -> initial charge (ℤ or rationals×k)

@dataclass(frozen=True)
class Rule:
    """A local redistribution: from a vertex of `from_deg` send `amount` to each
    neighbor matching `to_pattern`, within radius `radius`. Conserves total charge."""
    from_deg: int
    to_pattern: str                    # small predicate on the neighbor's local type
    amount: int
    radius: int = 1

@dataclass(frozen=True)
class DischargingArgument:
    D: int                             # regime (9 for v1)
    charge: Charge
    rules: tuple[Rule, ...]
    forbidden: tuple[str, ...]         # graph6 cores from the reducible set 𝒞
```

### B2. The verifier — `discharging_unavoidable(arg) -> Claim`

Given a `DischargingArgument`, the tool **verifies unavoidability** (it does not invent the
argument — the model/human proposes `charge` + `rules`; the tool checks):

1. **Global identity.** Compute the total initial charge bound over any `D`-critical
   `K_D`-free graph from `μ` and the degree constraint (Σ μ(d(v)) has a sign forced by the
   degree distribution). Establish the target contradiction value (e.g. total < 0).
2. **Conservation.** Verify each `Rule` moves charge without creating/destroying it
   (send = receive); reject non-conserving rule sets.
3. **Local discharge check (the finite core).** Enumerate every local neighborhood type up
   to the max rule `radius`, with vertex degrees in `{D−1, D}` (finite via `geng` /
   bounded local enumeration). For each type, **either** it contains a forbidden core from
   `𝒞` (excluded — it can't occur in a graph avoiding 𝒞) **or** apply the rules and check
   the vertex's final charge meets the required bound.
4. **Verdict.** If every non-excluded local type meets the bound while the global identity
   forces the opposite sign ⇒ **UNAVOIDABLE**: any `D`-critical `K_D`-free graph avoiding
   `𝒞` is charge-infeasible, so it must contain some member of `𝒞`. Mint a
   python-checked/enumeration Claim: "`𝒞` is unavoidable in `D`-critical `K_D`-free graphs
   (D=…)". Otherwise return the offending local type(s) as a **MISS** (the argument does
   not close — here is the neighborhood that survives), minting nothing. Never claim
   "avoidable."

Logical form, stated in the tool doc: **UNAVOIDABLE is sufficient** for the discharging
half; a MISS returns a concrete counter-neighborhood (the thing to forbid next or the rule
to fix) and proves nothing. Mirror `reducible_configuration`'s one-directional honesty.

### B3. Arg model / registry / category

`DischargingArgs(D, mu, rules, forbidden)` in `arg_models.py`; register
`discharging_unavoidable` in `registry.py`, category `reduction`. The model supplies `mu`
and `rules` as JSON; the code builds the `DischargingArgument` and derives everything else
(same "code derives, model proposes" discipline as `reducible_configuration`).

### B4. Budget + honesty guards

- Cap local-enumeration radius (v1: radius ≤ 1; radius 2 explodes) and neighborhood count;
  surface `ToolBudgetExceeded` rather than hang.
- The forbidden set `𝒞` passed in must be cores already **minted reducible** on the ledger
  (the tool cross-checks against ledger Claims); you cannot discharge against unproven
  configs. This couples the two halves honestly.

---

## Part C — The bridge lemma (fidelity anchor, formal tier)

`Literature/Coloring/BK_DischargingClosure/`, a `stated` entry:

> **`reducible_and_unavoidable_imp_no_counterexample`**: fix `D`. If every configuration in
> a finite set `𝒞` is reducible (absent from any `D`-critical `K_D`-free graph — from
> `reducible_of_fChoosable`) and `𝒞` is unavoidable (every `D`-critical `K_D`-free graph
> contains some `C ∈ 𝒞`), then there is no `D`-critical `K_D`-free graph; hence every graph
> with `Δ = D` and `ω < D` is `(D−1)`-colorable — Borodin–Kostochka at `D`.

This is the discharging counterpart of `reducible_of_fChoosable`, and it is what lets a
completed reducible-set + unavoidability-certificate settle BK **at D = 9**. Until proved,
any "BK at D=9" claim is conditional on it — carry the tag, exactly as with the
reducibility bridge. Ship SanityChecks (a concrete small `𝒞`/critical instance).

**Settlement note:** a genuine reducible-∧-unavoidable pair at D=9 does **not** trip the
`borodinKostochka` (all-Δ≥9) settlement check — it settles the D=9 slice. Add a separate,
kernel-verified `settles_bk_at` recognizer (same defeq discipline as the D-general one) so
the campaign can register "BK proved at Δ=9" as a real milestone without falsely claiming
the full conjecture. Do **not** let a D=9 result flip the general `borodinKostochka`.

---

## Part D — Mission / staircase integration

`MISSION_BK` and the staircase gain the discharging half. New rung order:

1. Durable `lean_prove` of the reducibility bridge (`reducible_of_fChoosable`).
2. Re-derive Rabern's seed configs (Part A), then extend the reducible set `𝒞`.
3. **Propose a discharging argument** (`charge` + `rules`) and run `discharging_unavoidable`
   against the current `𝒞`; on a MISS, forbid the returned counter-neighborhood (back to
   rung 2 with a *targeted* new core) or repair the rules. This is the loop that composes.
4. Durable `lean_prove` of the discharging closure bridge (Part C).
5. Assemble: reducible `𝒞` + unavoidability certificate ⇒ **BK at Δ=9**.

The staircase snapshot should show both halves: `𝒞` size, and the best discharging attempt
(closed / which neighborhood survived). Progress is now a two-dimensional stair that can
actually reach a landing at D=9 — the reducibility count alone never could.

---

## Scope discipline (read this before building)

- **v1 is D = 9 only.** That's where degrees are bounded and discharging is finite — and
  it's the open crux (Reed handles large D). General D is a symbolic/parameterized
  discharging argument: v2, explicitly deferred.
- **The tool verifies; it does not invent.** Finding `μ`, the rules, and the right `𝒞` is
  the hard creative act (model + human). The engine makes a proposed argument *checkable
  and bankable*, and makes the search structured — it does not promise to find one.
  Success is not guaranteed; BK at Δ=9 is open. Say so.
- **Sufficient-only, both halves.** Reducible: a hit forbids, a miss is silent.
  Unavoidable: a hit closes, a miss returns a surviving neighborhood and proves nothing.
  No code path may emit "avoidable" or "not reducible."
- **Couple the halves via the ledger.** `discharging_unavoidable` may only use forbidden
  cores already minted reducible; the closure bridge may only fire when both a reducible
  `𝒞` and an unavoidability certificate over that same `𝒞` are on the ledger.
- Radius-1 rules first; guard enumeration blow-up.

## Self-test — `ci/discharging_self_test.py`

- **Closes (must UNAVOIDABLE):** a toy regime + tiny `𝒞` with a hand-checked charge/rule
  set that provably closes; assert the tool returns UNAVOIDABLE.
- **Survives (must MISS, silent):** the same with one forbidden core removed, so a
  neighborhood survives; assert MISS + a returned counter-neighborhood + no Claim.
- **Non-conserving rules (must reject):** a rule set that creates charge; assert rejection.
- **Ledger coupling:** `discharging_unavoidable` refuses a `𝒞` containing a core not minted
  reducible.
Wire into CI alongside `reduction_self_test.py`.

## Acceptance

- `reducible_seeds.toml` + `campaign.py` wiring; staircase cites next un-minted seed.
- `discharging/` engine + `discharging_unavoidable` tool (category `reduction`), verifier
  per B2, budget + ledger-coupling guards, one-directional honesty.
- `BK_DischargingClosure` stated entry + SanityChecks; conditional tag on D=9 claims.
- `settles_bk_at` D=9 recognizer (kernel defeq), separate from the general settlement;
  D=9 never flips general `borodinKostochka`.
- `MISSION_BK` + staircase carry the discharging rungs.
- `discharging_self_test.py` green; `ruff`/`pytest` green.
