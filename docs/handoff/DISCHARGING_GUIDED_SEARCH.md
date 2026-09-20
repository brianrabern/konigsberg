# Guided discharging search — use the survivor as a gradient (Cursor spec)

*Today the loop is: model guesses a full charge/rule set → `discharging_unavoidable`
says HIT or MISS. On a MISS the engine already returns the **surviving neighborhood** —
the exact local configuration the argument failed to rule out — and we throw that signal
away. This spec turns it into a gradient: a search that iteratively kills survivors,
mechanizing the part that doesn't need a model (covering a survivor with a catalog config)
and reserving the model for the residual. It converts "hope the model proposes a closing
argument" into "systematically drive the survivor count to zero." Highest-leverage change
available, and it builds entirely on tooling that already exists.*

Depends on: the discharging engine (`konigsberg_empirical/discharging/engine.py`,
`discharging_unavoidable`), the ingested catalog (`rabern_bk_catalog.toml`, 5,008 configs),
the reducibility bridge (`reducible_of_fChoosable`), and the closure lemma
(`BK.reducible_and_unavoidable_imp_no_counterexample`). v1 targets **D = 9**.

---

## The idea in one paragraph

A discharging argument `(μ, rules, 𝒞)` **closes** when every local neighbourhood type
(degrees in {D−1, D}) either contains a member of the forbidden set `𝒞` or ends
charge-feasible. A MISS returns the neighbourhoods that do neither — the **survivors**.
Two levers kill a survivor: (a) **forbid it** — add to `𝒞` a reducible config that is an
induced subgraph of the survivor (mechanical: search the catalog); or (b) **re-charge it**
— tweak `μ`/`rules` so it ends feasible (creative: the model, or a rule-mutation library).
Lever (a) is mechanizable and, with Landon's 5,008-config catalog, covers a large fraction
of survivors with no model involvement. Reserve the model for the residual survivors that
**no** catalog config covers — those are the real obstructions.

## WP1 — Enrich the MISS result (the gradient signal)

`discharging_unavoidable` currently returns *a* survivor. Change it to return the full,
ranked survivor set with structured reasons:

```python
@dataclass(frozen=True)
class Survivor:
    neighborhood: str        # graph6 of the local type that survived
    reason: str              # "charge-infeasible at center" | "no 𝒞 member inside" | …
    deficit: int             # how far from feasible (for ranking; smaller = closer)

@dataclass(frozen=True)
class DischargeResult:
    closed: bool
    survivors: tuple[Survivor, ...]   # empty iff closed
    checked: int                      # neighbourhood types enumerated
```

Rank survivors by `deficit` (closest-to-covered first) so the search attacks the easiest
gaps first. This is a pure refactor of the existing verifier — no new math.

## WP2 — Mechanical cover search (`discharging_cover`)

New empirical helper + tool:

```python
def discharging_cover(survivor_g6: str, catalog: list[str]) -> str | None:
    """Return a catalog config that is an INDUCED SUBGRAPH of the survivor
    (so adding it to 𝒞 kills this survivor), or None. Prefer the smallest, and
    prefer offline/AT (f-choosable, proof-usable) over online (needs paintability
    bridge). Induced-subgraph test on ≤ D-vertex graphs is cheap."""
```

Index the catalog by vertex count / degree sequence so the induced-subgraph sweep over
5,008 configs stays fast. This is the workhorse: most survivors at D=9 will contain a
small reducible config, and finding it needs no model.

## WP3 — The search loop (`discharging_search`)

Harness-level driver (or a single agent tool that runs the loop internally):

```
active_𝒞 = seed set (small; e.g. the offline/AT configs already minted)
best = None
for _ in range(max_iters):
    r = discharging_unavoidable(μ, rules, active_𝒞)
    record(survivor_count=len(r.survivors), size_𝒞=len(active_𝒞))   # dashboard signal
    if r.closed:
        return CLOSED(μ, rules, active_𝒞)
    progress = False
    for s in r.survivors:                      # (a) mechanical: cover from catalog
        cover = discharging_cover(s.neighborhood, catalog)
        if cover and cover not in active_𝒞:
            active_𝒞.add(cover); progress = True
    if not progress:                           # (b) creative: recharge / new config
        move = propose_mutation(μ, rules, r.survivors)   # model OR rule-library
        if improves(move):                     # fewer/only-smaller-deficit survivors
            (μ, rules) = move; progress = True
    if not progress:
        return STUCK(best=(μ, rules, active_𝒞), residual=r.survivors)
```

Key properties:
- **Monotone progress signal.** Survivor count (and total deficit) should trend down;
  expose it to the dashboard so a human sees the search converging or plateauing —
  vastly more informative than "0 closed".
- **Model only on the residual.** `propose_mutation` is invoked only when the catalog
  can't cover — i.e. exactly the creative sub-problem. The 27B's weakness at proposing
  whole arguments stops mattering; it only nudges rules against a handful of specific,
  displayed survivors.
- **STUCK is a result, not a failure.** The residual survivors when stuck are the precise
  local configurations that neither Landon's catalog nor the current charging can rule
  out — a genuine, human-legible obstruction to closing BK at Δ=9. Mint them as a
  `python-checked` "irreducible-frontier" Claim (NOT a forbidden-config claim): this is
  the lead the whole hunt exists to produce.
- **Track recurring survivors** across iterations; a survivor that keeps reappearing under
  different rules is the stable obstruction — surface it.

## WP4 — Trust / two-tier (do not let the search launder unproven reducibility)

- A survivor "covered" by an **offline/AT** catalog config is proof-usable (the proved
  `reducible_of_fChoosable` bridge certifies it). A survivor covered only by an **online /
  k-fold** config is *empirically* covered but needs the paintability/k-fold bridge before
  it can enter a kernel proof — tag it, don't silently count it as proof-grade.
- On CLOSED, mint the unavoidability Claim **conditional on**: the closure lemma
  `BK.reducible_and_unavoidable_imp_no_counterexample`, AND every member of the final
  `active_𝒞` carrying a reducibility certificate. Report `active_𝒞`, `μ`, `rules`
  verbatim so the argument is reproducible and referee-checkable. A CLOSED result over an
  all-offline/AT `𝒞` is a proof-grade BK@9 attempt; one that leans on online configs is
  an empirical closure pending the stronger bridge — say which.
- The referee must treat a discharging closure like any other claim: re-run
  `discharging_unavoidable` on the reported `(μ, rules, 𝒞)` independently, and verify each
  `𝒞` member's reducibility certificate.

## WP5 — Instrumentation + self-test

- Dashboard: expose `survivor_count`, `total_deficit`, `size_𝒞`, `iterations`, and the
  top residual survivor to `hunt_watch.py` (a "discharging search" panel). Falling
  survivor count is the progress metric for the whole campaign now.
- `ci/discharging_search_self_test.py`: (1) a toy regime with a known closing argument —
  assert the search reaches `closed` (survivor_count → 0); (2) a regime that cannot close
  with the given catalog — assert it returns STUCK with a non-empty, stable residual and
  mints the irreducible-frontier Claim, not a false closure.

## Acceptance

- `discharging_unavoidable` returns the full ranked `Survivor` set with reasons/deficits.
- `discharging_cover` finds induced-subgraph covers from the catalog (offline/AT preferred),
  indexed for speed.
- `discharging_search` runs the loop: mechanical cover first, model/rule-library on the
  residual, monotone survivor-count signal, STUCK returns the residual as an
  irreducible-frontier Claim, CLOSED mints a (conditional, two-tier-tagged) unavoidability
  Claim with the argument attached.
- Dashboard shows the survivor-count trend; self-test green (closes the toy, reports the
  residual on the unclosable one).
- `ruff`/`pytest` green; fail-closed and trust invariants unchanged.

## Scope discipline

- v1: cover-from-catalog + a small rule-mutation library, D = 9. LP-based rule discovery
  (systematic charge redistribution) is the natural v2 and removes the model from the
  residual step too — out of scope here.
- Sufficient-only, as ever: the search can *close* (forbid a set unavoidably) or report a
  residual; it never asserts a set is *avoidable*.
- The realistic outcome for a long run is a shrinking survivor count and a small stable
  residual — the obstruction — not a full closure. That residual is the deliverable a
  human mathematician would actually want. Build for that outcome, not just the jackpot.
