"""Formal-tier tools. Each returns a ledger Claim with a LEAN_KERNEL trust root.

    lean_check              typecheck against live env; goal state + errors
    lean_typecheck_statement statement well-formedness w/o proof
                             (catches "proved the wrong thing")
    lean_eval               #eval / #reduce; decidable computation in Lean
    lean_search             exact?/apply?/Loogle over mathlib + own library
    lean_prove              elaborate a proof (optionally durable / corpus-fresh)
    lean_add_to_library     GATED commit of an accepted lemma (behind check_axioms)
    reset_env / retract     session-env hygiene
"""
from __future__ import annotations

import re

from ..lean_repl import GoalState, LeanREPL, LeanREPLError
from ..ledger import Claim, mint_lean_proof, mint_lean_statement
from ..lemmas import HOLE_AXIOMS

_SEARCH_TACTICS = ("exact?", "apply?")

# `exact?`/`apply?` print candidates as "Try this: <tactic>" (singular) or a
# "Try these:" header followed by • / · bulleted tactics.
_SUGGESTION = re.compile(r"Try (?:this|these):\s*(.*)")
_BULLET = re.compile(r"^\s*[•·]\s*(.+)$")
# Live REPL commands run *after* DEFAULT_SCRATCH_PREAMBLE. A later `import`
# is a parse error ("must be used in the beginning of the file") and is the
# usual Eva miss: it pastes `import Mathlib` into lean_prove.
_IMPORT_LINE = re.compile(r"^\s*import\s+\S+")


def strip_repl_imports(snippet: str) -> tuple[str, list[str]]:
    """Drop ``import …`` lines. Scratch env already loaded Konigsberg + Tactic."""
    stripped: list[str] = []
    kept: list[str] = []
    for line in snippet.splitlines(keepends=True):
        if _IMPORT_LINE.match(line):
            stripped.append(line.strip())
        else:
            kept.append(line)
    return "".join(kept).strip(), stripped


def format_compile_miss(
    lean_name: str,
    errors: list[str] | str,
    *,
    durable: bool = False,
    stripped_imports: list[str] | None = None,
    missing_decl: bool = False,
) -> str:
    """Short, actionable lean_prove failure — compile miss, not a kernel proof."""
    if isinstance(errors, str):
        msgs = [errors] if errors.strip() else []
    else:
        msgs = [str(e).strip() for e in errors if str(e).strip()]
    first = re.sub(r"\s+", " ", msgs[0]) if msgs else "(no Lean message)"
    if len(first) > 400:
        first = first[:397] + "..."
    extra = ""
    if stripped_imports:
        extra = (
            " Dropped illegal `import` lines (scratch env already has "
            "Konigsberg + Mathlib.Tactic)."
        )
    if missing_decl:
        return (
            f"LEAN COMPILE MISS `{lean_name}`: snippet had no errors but that "
            f"name is not in the env. Declare `theorem {lean_name}` at the top "
            f"level (not only inside a namespace).{extra} "
            "Fix the snippet or abandon this lemma — do not resubmit the same text."
        )
    kind = "durable, " if durable else ""
    return (
        f"LEAN COMPILE MISS ({kind}not a kernel proof) `{lean_name}`: {first}."
        f"{extra} Fix the snippet or abandon this lemma — do not resubmit the "
        "same text. Do not `import` (preamble already loaded)."
    )


def _axioms_or_miss(
    repl: LeanREPL,
    lean_name: str,
    *,
    timeout_s: float | None,
    durable: bool,
    stripped: list[str],
) -> tuple[str, ...]:
    try:
        axioms = tuple(repl.print_axioms(lean_name, timeout_s=timeout_s))
    except LeanREPLError as exc:
        raise ValueError(
            format_compile_miss(
                lean_name,
                str(exc),
                durable=durable,
                stripped_imports=stripped,
                missing_decl=True,
            )
        ) from exc
    holes = sorted(HOLE_AXIOMS.intersection(axioms))
    if holes:
        raise ValueError(
            format_compile_miss(
                lean_name,
                f"uses {', '.join(holes)} (sorry/admit is not a kernel proof)",
                durable=durable,
                stripped_imports=stripped,
            )
        )
    return axioms


def _parse_suggestions(text: str) -> list[str]:
    """Extract suggested tactic snippets from search-tactic output, in order."""
    out: list[str] = []
    for line in text.splitlines():
        m = _SUGGESTION.search(line)
        if m:
            snippet = m.group(1).strip()
            if snippet:  # "Try these:" header carries no snippet itself
                out.append(snippet)
            continue
        b = _BULLET.match(line)
        if b:
            out.append(b.group(1).strip())
    seen: set[str] = set()
    return [s for s in out if not (s in seen or seen.add(s))]


def lean_check(repl: LeanREPL, snippet: str) -> GoalState:
    body, _stripped = strip_repl_imports(snippet)
    repl.ensure_preamble()
    return repl.send(body or snippet)


def lean_typecheck_statement(
    repl: LeanREPL, statement: str, *, timeout_s: float | None = None
) -> Claim:
    """Well-formed-only: the statement elaborates (as a proposition). Says NOTHING
    about truth. Its job is to catch "proved the wrong thing" — a statement that
    doesn't even parse/elaborate — before any proof effort is spent. Raises if the
    statement fails to elaborate; otherwise mints a `stated` Claim.
    """
    repl.ensure_preamble(timeout_s=timeout_s)
    # Transactional: a failed `example := sorry` must not poison the session env.
    state = repl.send_transactional(
        f"example : {statement} := sorry", timeout_s=timeout_s
    )
    if not state.ok:
        raise ValueError(f"statement does not elaborate: {state.errors}")
    return mint_lean_statement(statement, tool="lean_typecheck_statement")


def lean_prove(
    repl: LeanREPL,
    lean_name: str,
    snippet: str,
    *,
    durable: bool = False,
    timeout_s: float | None = None,
) -> Claim:
    """Elaborate a full proof; on success mint a proof Claim carrying #print axioms.

    When ``durable=True``, elaborate in a **fresh corpus env** (committed Konigsberg
    + Mathlib.Tactic only — no accumulated session decls). Success ⇒ the snippet is
    self-contained and promotable; the Claim records ``durable=True``. The session
    env is restored afterward (durable prove does not pollute or replace it).

    When ``durable=False`` (default), elaborate transactionally against the session
    env: commit only on full success. A failed elaboration leaves no declaration
    behind. Session-only proofs are tagged ``[session-only]`` and are not promotable.

    Compile misses raise ``ValueError`` with a ``LEAN COMPILE MISS`` banner
    (truncated first Lean error + what to do). They never mint a proof Claim.
    Leading ``import`` lines are stripped: the scratch env already loaded them.
    """
    body, stripped = strip_repl_imports(snippet)
    if not body:
        raise ValueError(
            format_compile_miss(
                lean_name,
                "snippet was only `import` lines",
                durable=durable,
                stripped_imports=stripped,
            )
        )

    if durable:
        snap = repl.snapshot()
        try:
            repl.load_preamble(timeout_s=timeout_s if timeout_s is not None else 300)
            state = repl.send_transactional(body, timeout_s=timeout_s)
            if not state.ok:
                raise ValueError(
                    format_compile_miss(
                        lean_name,
                        state.errors,
                        durable=True,
                        stripped_imports=stripped,
                    )
                )
            axioms = _axioms_or_miss(
                repl, lean_name, timeout_s=timeout_s, durable=True, stripped=stripped
            )
            claim = mint_lean_proof(
                statement=lean_name,
                axioms=axioms,
                tool="lean_prove",
                durable=True,
            )
        finally:
            repl.restore(snap)
        # Durable prove restores the old env pointer, which does not contain the
        # new decl. Install it into the session env so later lemmas can use it.
        try:
            repl.ensure_preamble(timeout_s=timeout_s)
            inst = repl.send_transactional(body, timeout_s=timeout_s)
            _ = inst.ok
        except Exception as exc:  # noqa: BLE001 — Claim already minted; install is best-effort
            _ = exc
        return claim

    repl.ensure_preamble(timeout_s=timeout_s)
    state = repl.send_transactional(body, timeout_s=timeout_s)
    if not state.ok:
        raise ValueError(
            format_compile_miss(
                lean_name, state.errors, stripped_imports=stripped
            )
        )
    axioms = _axioms_or_miss(
        repl, lean_name, timeout_s=timeout_s, durable=False, stripped=stripped
    )
    return mint_lean_proof(
        statement=lean_name, axioms=axioms, tool="lean_prove", durable=False
    )


def lean_search(
    repl: LeanREPL, goal: str, *, tactic: str = "exact?", timeout_s: float | None = None
) -> list[str]:
    """Search mathlib + the own library for lemmas bearing on `goal`.

    Runs `example : <goal> := by <tactic>` (tactic in exact?/apply?) and returns
    the tactic snippets the search suggests, e.g. "exact Foo.bar". These are
    CANDIDATES, not verified facts: a suggestion is only trustworthy once run and
    typechecked (via lean_prove). Hence this returns plain strings and mints no
    Claim. Returns [] when the search finds nothing.
    """
    if tactic not in _SEARCH_TACTICS:
        raise ValueError(f"tactic must be one of {_SEARCH_TACTICS}, got {tactic!r}")
    repl.ensure_preamble(timeout_s=timeout_s)
    # Search examples should not stick in the session env.
    state = repl.send(
        f"example : {goal} := by {tactic}", timeout_s=timeout_s, commit=False
    )
    return _parse_suggestions("\n".join([*state.infos, *state.errors]))


def reset_env(repl: LeanREPL, notebook: object | None = None) -> str:
    """Drop ephemeral session decls; reload preamble; replay locked lemmas."""
    repl.reset_env(timeout_s=300)
    from ..lemmas import LemmaNotebook, replay_locked_lemmas

    nb = notebook if isinstance(notebook, LemmaNotebook) else None
    if nb is None or not nb.lemmas:
        return "session env reset to clean corpus preamble (all session decls dropped)"
    ok, errors = replay_locked_lemmas(repl, nb, timeout_s=300)
    msg = (
        "session env reset to clean corpus preamble; "
        f"replayed {ok}/{len(nb.lemmas)} locked lemmas"
    )
    if errors:
        msg += " — " + "; ".join(errors[:3])
    return msg


def retract(repl: LeanREPL, name: str) -> str:
    """Drop the session declaration ``name`` and rebuild remaining session cmds."""
    repl.retract(name, timeout_s=300)
    return f"retracted session declaration {name!r}; remaining session cmds replayed"


def lean_add_to_library(
    repl: LeanREPL,
    lean_name: str,
    snippet: str,
    *,
    area: str,
    citation: str,
    informal_statement: str,
    referee_report: object,
    sanity_snippet: str | None = None,
    confirmed: bool = False,
    formal_root: object = None,
    run_gates: bool = True,
    source_claim: Claim | None = None,
) -> Claim:
    """Commit only after referee accept + human confirm + axiom/sanity gates.

    Never automatic. See ``tools.library_writeback.lean_add_to_library``.
    """
    from pathlib import Path

    from .library_writeback import lean_add_to_library as _write

    return _write(
        repl,
        lean_name,
        snippet,
        area=area,
        citation=citation,
        informal_statement=informal_statement,
        referee_report=referee_report,  # type: ignore[arg-type]
        sanity_snippet=sanity_snippet,
        confirmed=confirmed,
        formal_root=Path(formal_root) if formal_root is not None else None,
        run_gates=run_gates,
        source_claim=source_claim,
    )
