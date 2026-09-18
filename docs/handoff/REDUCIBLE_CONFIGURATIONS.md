# Reducible-configuration engine (Cursor spec)

*Everything Konigsberg has succeeded at is **verification-shaped**: given a fixed
object or a finite range, check a property. BK progress is **reduction-shaped**: prove
that a minimal counterexample cannot contain a local configuration. These look
incompatible — but reducibility of a configuration is itself a **finite, decidable,
list-coloring** question. That is the bridge. This engine turns "make progress on
Borodin–Kostochka" into "grow a verified set of forbidden configurations," each one a
real, human-legible micro-lemma of exactly the kind Cranston–Rabern trade in, and each
one checkable by the list-coloring solver you already have.*

This does **not** aim to prove BK. It aims to make Konigsberg produce leads a human
would chase, and to make "did we make progress?" a countable question: *how many
proven-reducible configurations, and are any new?*

---

## The mathematics, pinned (read before coding — the whole design rests on it)

**Borodin–Kostochka.** If Δ(G) ≥ 9 and G is K_Δ-free then χ(G) ≤ Δ−1.

**Minimal counterexample.** A minimal counterexample `G` satisfies, writing `D := Δ(G)`:
- `D ≥ 9`;
- `ω(G) ≤ D−1` (K_D-free);
- `χ(G) = D` (Brooks gives χ ≤ D once G is not complete / an odd cycle, which K_D-free,
  D≥9 guarantees);
- **vertex-critical**: `χ(G − v) = D − 1` for every `v`, so **every proper subgraph is
  (D−1)-colorable**, and consequently `δ(G) ≥ D − 1`.

These four facts are the standing hypotheses `H_BK`. They are what the tool gets to
assume for free.

**Configuration.** A `core` `K` (a small graph) together with a **degree spec**: for
each core vertex `v`, its total degree `d_G(v)` in the ambient `G` (with `deg_K(v) ≤
d_G(v) ≤ D`). The claim under test: *no minimal counterexample contains this core with
these degrees as an induced subgraph.*

**Reducibility (the decidable core).** Suppose `G` contains the configuration. Delete
the core `K`; by criticality the rest `G − K` has a (D−1)-coloring. Each core vertex
`v` has `d_G(v) − deg_K(v)` neighbours **outside** `K`, already colored, forbidding at
most that many colors. So `v` may be colored from a list of size at least

```
f(v) := (D − 1) − (d_G(v) − deg_K(v)) = (D − 1) − d_G(v) + deg_K(v).
```

If the core `K` can be list-colored **for every** adversarial choice of those forbidden
sets, then `G` itself is (D−1)-colorable — contradicting `χ(G) = D`. So the
configuration **cannot occur**: it is *forbidden* in every minimal counterexample.

**The exact logical form (this is the fidelity-critical part).** The real adversary is
constrained (two outside-neighbours of the same color forbid only one color; adjacent
outside-neighbours get different colors; the palette is exactly D−1). Testing full
`f`-choosability of the core — each vertex gets an *arbitrary* list of size `f(v)` —
**over-approximates** that adversary. Therefore:

> **K is f-choosable  ⟹  configuration reducible  ⟹  forbidden in a minimal
> counterexample.**

**One direction only.** A hit (core is f-choosable) is a genuine forbidden
configuration. A miss (core is *not* f-choosable) proves **nothing** — the real
constrained adversary may still lose. This is the same "sufficient-only, a miss is
silent" shape as `alon_tarsi`, and the tool statement must say so in those words. Do
**not** let the tool ever emit "configuration is NOT reducible."

`D` need not be fixed. `f(v)` depends on `D` only through `(D−1) − d_G(v)`, i.e. through
the **degree slack** `s(v) := (D−1) − d_G(v) + deg_K(v)`. For low vertices `d_G(v) =
D−1` so `f(v) = deg_K(v)` — independent of `D`. So a configuration built entirely from
low vertices gives a `D`-uniform forbidden lemma in one shot. Parameterize by slack, not
by `D`.

---

## WP1 — The reducibility computation (`konigsberg_empirical/reduction/`)

New empirical package `konigsberg_empirical/reduction/reducible.py`. Pure Python, no
Lean. It **reuses the existing choosability solver** — do not write a new list-coloring
engine.

```python
@dataclass(frozen=True)
class Configuration:
    core: Graph                 # the core K (internal graph6 / Graph object)
    f: dict[int, int]           # f(v): worst-case list size per core vertex, ≥ 1
    # provenance of f: either explicit degrees + D, or "low-vertex" (D-uniform)
    degree_spec: dict[int, int] # d_G(v) per core vertex, for the human-facing statement
    D: int | None               # None ⇒ low-vertex / D-uniform config

def reducible(config: Configuration) -> ReduceResult:
    """Return HIT (core is f-choosable ⇒ forbidden), or MISS (silent: proves nothing).

    HIT is decided by the existing choosability machinery: the core is f-choosable
    iff there is NO bad f-list, checked exhaustively to the complete palette. Reuse
    konigsberg_empirical.coloring.choosability — the SAME find_bad_list / verify path
    that choosability_refute uses, generalized from uniform k to per-vertex f(v).
    """
```

Implementation notes, concrete:
- `choosability.find_bad_list(graph, k, palette=...)` currently takes a **uniform** `k`.
  Generalize it (or add `find_bad_list_f(graph, f: dict, palette)`) to per-vertex list
  sizes. The CEGAR/SAT core is unchanged; only the list-size vector differs. Keep the
  uniform entry point working (it's `f(v) ≡ k`).
- **HIT** = no bad `f`-list exists up to the complete palette (`max f(v) · n` suffices,
  as in the uniform case) ⇒ core is `f`-choosable ⇒ reducible. This is an **exhaustive**
  result → `ENUMERATION` root (python-checked), exactly like a `choosability_refute`
  miss that reaches completeness.
- **MISS** = a bad `f`-list exists ⇒ over-approximation failed ⇒ **silent**. Return a
  result the tool renders as "not established (method inconclusive)" — never a negative
  claim.
- Guard `f(v) ≥ 1`; if any `f(v) ≤ 0` the configuration is out of scope for this method
  (a core vertex with no slack) — return a clean "out of scope" MISS, don't crash.
- Sanity-clamp core size (say `|K| ≤ 12`) and palette; a runaway `f`-choosability check
  is the obvious DoS. Surface a `ToolBudgetExceeded` rather than hang.

The `Configuration` builder must **derive `f` from the degree spec**, never accept a
hand-supplied `f` from the model — same discipline as "never hand-write a graph6." The
model proposes `(core, degrees, D)`; the code computes `f`.

---

## WP2 — The agent tool (`reducible_configuration`)

Wrapper in `harness/konigsberg_harness/tools/empirical_tools.py`, arg model in
`arg_models.py`, registered in `registry.py`, categorized in `fundamentals_tools.py`'s
category map (new category `"reduction"` at the end of `CATEGORY_ORDER`).

```python
class ReducibleConfigurationArgs(BaseModel):
    core: str                       # graph6 of the core K (via make_graph, never hand-written)
    degrees: dict[str, int] | list[int]   # d_G(v) per core vertex (ambient degree)
    D: int | None = None            # Δ of the ambient counterexample; None ⇒ low-vertex/D-uniform
```

```python
def reducible_configuration(core, degrees, D=None) -> Claim:
    """Test whether a local configuration is reducible in a minimal BK counterexample
    (H_BK: Δ=D≥9, K_D-free, D-critical). Builds f(v) = (D-1) - d_G(v) + deg_K(v) from
    the degree spec, then tests f-choosability of the core via the choosability solver.

    HIT  → core is f-choosable ⇒ configuration FORBIDDEN in every minimal counterexample
           (certificate/enumeration-rooted). SUFFICIENT ONLY.
    MISS → method inconclusive; proves NOTHING (the real adversary is weaker than
           arbitrary f-lists). Never emits a 'not reducible' claim.
    """
```

Tool doc string must state, verbatim in spirit: *"f-choosability of the core is
SUFFICIENT for reducibility, not necessary — a miss proves nothing, exactly like
alon_tarsi. Requires the H_BK hypotheses; the forbidden-configuration conclusion is
conditional on the reducibility bridge lemma (WP4)."*

---

## WP3 — Ledger claim shape

A HIT mints (via `mint_enumeration`, `ENUMERATION`/python-checked — the `f`-choosability
check is exhaustive-to-completeness, not a re-checked certificate object):

```
FORBIDDEN CONFIGURATION (BK minimal counterexample, Δ=D≥9, K_D-free, D-critical):
core=<graph6>, degree spec d_G=<...>, slack f=<...>; core is f-choosable
(exhaustive to palette P) ⇒ reducible ⇒ absent from every minimal counterexample.
[conditional on reducibility bridge lemma BK.reducible_of_fChoosable]
```

Non-negotiable in the statement string:
- name the **hypotheses** `H_BK` explicitly (so the claim is never read unconditionally);
- record `D` or mark **D-uniform**;
- carry the **`[conditional on bridge lemma …]`** tag until WP4 lands — the tool
  computes `f`-choosability (solid); the step *`f`-choosable ⇒ forbidden* is a
  **mathematical bridge**, and per the fidelity discipline it must be an explicit,
  named, referee-checkable lemma, not silently baked into a Python tool. This is the
  exact `main`-class trap and we are not walking into it again.

A MISS mints **nothing** (like a failed search). It may return an informational,
non-Claim result the REPL renders in Commentary ("inconclusive: bad f-list found").

---

## WP4 — The reducibility bridge lemma (the fidelity anchor)

The tool's soundness rests on one lemma that must live in the formal tier, stated
(ideally proved), not assumed:

> **`BK.reducible_of_fChoosable`**: In a graph `G` with `χ(G) = D` in which `G − K` is
> (D−1)-colorable, if the core `K` is `f`-choosable for `f(v) = (D−1) − d_G(v) +
> deg_K(v)`, then `G` is (D−1)-colorable (contradiction). Hence the configuration is
> absent from any minimal counterexample.

Until this is a checked Literature entry, every forbidden-configuration Claim carries the
`[conditional on bridge lemma]` tag and is **not promotable**. This is the one place
where "the tool is correct" and "the statement means what it says" could diverge; the
referee's generalized faithfulness check (see REFEREE spec) must fire on any
forbidden-configuration Claim whose bridge lemma is still `sorry`/absent. Get the
`stated` entry in first (with SanityChecks per FIDELITY_GATES); prove it when able.

---

## WP5 — Self-test (prove the engine isn't a rubber stamp)

`ci/reduction_self_test.py`, planted fixtures with **known** answers, asserted:

1. **Known-reducible (must HIT).** A trivially f-choosable core — e.g. a single low
   vertex `deg_K = 0`, `f = 0`… no: pick a core where `f(v) ≥ deg` clearly holds, such
   as an edge with `f ≡ 2`, or a small tree that is f-choosable by a greedy degeneracy
   argument. Assert `reducible_configuration` returns HIT and mints a forbidden-config
   Claim tagged conditional.
2. **Known-not-establishable (must MISS, silently).** A core that is **not** f-choosable
   for its `f` (e.g. `K_{3,3}`-type or an even cycle at `f ≡ 2` where a bad list
   exists). Assert the tool returns MISS and mints **no** Claim, and in particular
   **never** a "not reducible" Claim.
3. **Out-of-scope (must not crash).** A degree spec forcing some `f(v) ≤ 0`. Assert a
   clean out-of-scope MISS.
4. **Bridge-tag present.** Assert every HIT Claim string contains the `[conditional on
   bridge lemma …]` tag while `BK.reducible_of_fChoosable` is unproved. This is the
   regression that stops the fidelity gap from silently reopening.

"An engine that reports everything reducible is worse than none" — same doctrine as the
audit and referee self-tests. Wire into CI.

---

## Acceptance

- `reduction/reducible.py` computes `f`-choosability of a core via the **existing**
  choosability solver (uniform `k` path preserved); HIT only on exhaustive-to-completeness.
- `reducible_configuration` tool registered, categorized `reduction`, doc states
  sufficient-only + H_BK + conditional-on-bridge, `f` derived from degrees (never
  model-supplied).
- HIT mints an `ENUMERATION` Claim naming `H_BK`, recording `D`/D-uniform, tagged
  `[conditional on bridge lemma]`; MISS mints nothing and never a negative claim.
- `BK.reducible_of_fChoosable` filed at least as a `stated` Literature entry with
  SanityChecks; forbidden-config Claims are non-promotable until it is proved.
- `ci/reduction_self_test.py` green (HIT / silent-MISS / out-of-scope / bridge-tag) and
  wired into CI; `ruff`/`pytest` green.

## Scope discipline

- **Sufficient-only, always.** The engine can *forbid* configurations; it can never
  certify one *occurs* or is "irreducible." A miss is silence. Any code path that emits a
  negative reducibility claim is a bug.
- **v1 is direct-extension reducibility** (f-choosability over-approximation). It will
  fire on some configurations and stay silent on many. That is expected and honest.
- **Kempe-chain reducibility is v2 and explicitly out of scope here.** Allowing recoloring
  of `G − K` before extending (the C-reducible vs D-reducible distinction from the Four
  Color Theorem) strictly strengthens the adversary model and catches far more configs,
  but it is much harder to implement soundly. Note it as the next lever; do not attempt
  it in v1.
- **Unavoidability / discharging is NOT in this spec.** Growing the forbidden set is one
  half of a reducibility+discharging proof; proving a forbidden set is collectively
  unavoidable is the harder, less-automatable half and is deliberately deferred. This
  engine's deliverable is *verified forbidden configurations*, counted — not a proof of BK.
- Reuse the choosability solver; do not fork a second list-coloring engine. The trust
  boundary and the CEGAR core are already sound — build on them.
