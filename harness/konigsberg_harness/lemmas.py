"""Working lemma notebook — proofs that stick for this investigation.

Literature write-back (``lean_add_to_library`` / ``/promote``) is the corpus
gate. This is the layer under it: every successful ``lean_prove`` locks
``(lean_name, snippet)`` on the session so later turns and ``--resume`` can
read the proof back and replay it into a fresh Lean env.

Does not mint Claims. Trust still comes from the ledger; this only retains
source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# Kernel holes — a snippet that elaborates with these is not a proof.
HOLE_AXIOMS = frozenset({"sorryAx", "Lean.ofReduceBool"})


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class LockedLemma:
    lean_name: str
    snippet: str
    durable: bool = False
    axioms: tuple[str, ...] = ()
    at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lean_name": self.lean_name,
            "snippet": self.snippet,
            "durable": self.durable,
            "axioms": list(self.axioms),
            "at": self.at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LockedLemma:
        return cls(
            lean_name=str(data["lean_name"]),
            snippet=str(data.get("snippet") or ""),
            durable=bool(data.get("durable", False)),
            axioms=tuple(data.get("axioms") or ()),
            at=str(data.get("at") or _utcnow()),
        )

    def render(self) -> str:
        tag = "durable" if self.durable else "session"
        return f"{self.lean_name} [{tag}] ({len(self.snippet)} chars)"


def lemma_has_hole(lemma: LockedLemma | None) -> bool:
    """True when the snippet used sorry/admit or native_decide."""
    if lemma is None:
        return False
    return bool(HOLE_AXIOMS.intersection(lemma.axioms))


@dataclass
class LemmaNotebook:
    """Mutable, name-keyed store. Same object is shared by Session, tools, Lean replay."""

    lemmas: list[LockedLemma] = field(default_factory=list)

    def lock(self, lemma: LockedLemma) -> LockedLemma:
        self.lemmas = [l for l in self.lemmas if l.lean_name != lemma.lean_name]
        self.lemmas.append(lemma)
        return lemma

    def drop(self, name: str) -> bool:
        before = len(self.lemmas)
        self.lemmas = [l for l in self.lemmas if l.lean_name != name]
        return len(self.lemmas) < before

    def get(self, name: str) -> LockedLemma | None:
        for lemma in reversed(self.lemmas):
            if lemma.lean_name == name:
                return lemma
        return None

    def replace(self, lemmas: list[LockedLemma]) -> None:
        self.lemmas = list(lemmas)

    def clear(self) -> None:
        self.lemmas = []

    def list_render(self) -> str:
        if not self.lemmas:
            return "(no locked lemmas)"
        return "\n".join(f"{i + 1}. {l.render()}" for i, l in enumerate(self.lemmas))


def lemma_list(notebook: LemmaNotebook) -> str:
    """Model-facing catalog of locked proofs (names, not full snippets)."""
    return notebook.list_render()


def lemma_read(notebook: LemmaNotebook, name: str) -> str:
    """Return the locked snippet for ``name``, or an error string."""
    lemma = notebook.get(name)
    if lemma is None:
        known = ", ".join(l.lean_name for l in notebook.lemmas) or "(none)"
        return f"no locked lemma named {name!r}. locked: {known}"
    tag = "durable" if lemma.durable else "session"
    axioms = ", ".join(lemma.axioms) or "(none reported)"
    return (
        f"{lemma.lean_name} [{tag}]\n"
        f"axioms: {axioms}\n"
        f"locked_at: {lemma.at}\n\n"
        f"{lemma.snippet}"
    )


def replay_locked_lemmas(repl: object, notebook: LemmaNotebook, *, timeout_s: float | None = None) -> tuple[int, list[str]]:
    """Re-elaborate locked snippets against the live env (resume / reset)."""
    ensure = getattr(repl, "ensure_preamble", None)
    send = getattr(repl, "send_transactional", None)
    if not callable(ensure) or not callable(send):
        return 0, ["replay skipped: Lean REPL missing transactional send"]
    ensure(timeout_s=timeout_s)
    ok = 0
    errors: list[str] = []
    for lemma in notebook.lemmas:
        if not lemma.snippet.strip():
            errors.append(f"{lemma.lean_name}: empty snippet")
            continue
        state = send(lemma.snippet, timeout_s=timeout_s)
        if getattr(state, "ok", False):
            ok += 1
        else:
            errs = getattr(state, "errors", None) or "elaboration failed"
            errors.append(f"{lemma.lean_name}: {errs}")
    return ok, errors
