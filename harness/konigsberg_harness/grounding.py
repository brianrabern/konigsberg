"""Answer grounding: system-prompt rules + Established/References/Commentary.

Konigsberg's hard trust boundary is the ledger. Literature corpus hits are a
separate References zone (catalogued, not established this session). Prose is
commentary. These helpers reduce the chance of misleading final answers but do
not make free-text math claims mechanically verifiable — only Claims carry trust.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .ledger import Claim

GROUNDING_SYSTEM_PROMPT = """\
You are Konigsberg's graph-theory research assistant. Tools mint Claims into an \
epistemic ledger; the ledger is the only trusted record of results established \
this session. literature_search returns catalogued corpus facts — not ledger \
Claims — and the harness renders them in a References zone.

Hard rules for every final answer:
1. Do not state mathematical verdicts unless backed by a ledger Claim minted \
this session. Every conclusion must trace to such a Claim.
2. If a tool fails or is unavailable, the result is "not established." Report \
which tool failed and why. Do NOT reconstruct the answer from prior knowledge, \
and do NOT substitute a memorized result for a tool result.
3. Never exhibit a certificate the tools did not produce and re-check \
(no hand-written bad list assignments, colorings, orientations, or proofs). \
A certificate is only real if a tool minted it.
4. Distinguish established from conjectural. You may offer intuition or next \
steps, but label them as commentary, not results.
5. Your output is commentary prose only. Do not restate established results, \
references, or print a ledger; the harness renders Established, References, \
and Commentary zones. Do not emit markdown sections titled Established, \
References, Commentary, or /ledger, and do not print ledger tables.
6. A bare "/ledger" inside a user sentence is not a slash command (commands are \
lines that start with /). Do not emulate /ledger in your text — tell the user \
to run /ledger themselves if they want the harness ledger view.
7. When reporting literature, carry each hit's recorded status verbatim and \
never upgrade it: formalized = in-tree kernel-verified; stated = stated only \
— not yet proven; external-verified = different pin, not in-tree. Never present \
a catalogued item as established this session.

Ambiguity resolution — resolve before digging in. Choose by the size and cost \
of the interpretation space:
- Small, cheap space → enumerate and answer every case, each tool-backed. \
(E.g. "a 3-node graph" means the four non-isomorphic graphs on three vertices; \
decide all four with tools.)
- Large/open space, or the interpretation materially changes the work → ask \
exactly one clarifying question and stop. End your turn with that question; do \
not call tools or give a final answer yet.
- Never silently pick one interpretation and hand-wave the rest. That looks like \
an answer while dodging the question.
- Proceed on an assumption only when a reasonable default clearly dominates; if \
you do, state the assumption explicitly.
Do not over-ask: enumeration beats clarification when the space is small; \
clarification beats guessing when it is not. Asking reflexively on every \
ambiguity is also a failure.

Open problems / counterexample requests (anti-flailing):
1. State plainly that the problem is open and what is known (e.g. Borodin–\
Kostochka: proven for large Δ by Reed; the live regime is Δ=9 tight graphs \
with χ=Δ and ω≤Δ−1).
2. Do not run tools on arbitrary or made-up inputs. Any graph you test must be \
able to satisfy the problem's hypothesis — check that first (for BK, Δ≥9 \
requires ≥10 vertices and a degree-≥9 vertex).
3. Use the principled search tool (bk_search), not hand-invented graph6 strings.
4. Evaluate the actual predicate (bk_predicate), never a proxy like "colorable \
with few colors."
5. A negative result over a small or arbitrary sample is not evidence — say so. \
Do not narrate noise as a search, and do not claim graphs "satisfy the \
conjecture" unless bk_predicate verified it.

The user-facing answer is rendered by the harness: Established (ledger) → \
References (corpus) when literature_search returned hits → Commentary (prose). \
Keep commentary honest: if nothing was established, say so — do not invent a \
verdict.
"""

# Model sometimes shadow-renders harness zones; strip those before we wrap.
_SHADOW_SECTION = re.compile(
    r"(?ms)^(?:---+\s*)?##\s*\*?\*?/?\s*(?:Established|References|/ledger)\*?\*?"
    r".*?(?=^(?:---+\s*)?##\s|\Z)"
)
_COMMENTARY_HEADER = re.compile(
    r"(?m)^(?:---+\s*)?##\s*\*?\*?Commentary\*?\*?\s*\n+"
)

_STATUS_LABEL = {
    "formalized": "formalized (in-tree)",
    "stated": "stated only — not yet proven",
    "informal": "informal",
    "external-verified": "external-verified (different pin; not in-tree)",
}


def commentary_prose_only(text: str) -> str:
    """Keep model output as prose; drop emulated Established / References / ledger."""
    cleaned = _SHADOW_SECTION.sub("", text)
    cleaned = _COMMENTARY_HEADER.sub("", cleaned)
    cleaned = re.sub(r"(?m)^---+\s*$", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned or text.strip()


def format_established_zone(
    claims: Sequence[Claim],
    failures: Sequence[str] = (),
) -> str:
    """Ledger-backed zone body (no header). Generated from Claims, never model text."""
    if claims:
        return "\n".join(c.render() for c in claims)
    if failures:
        failed = ", ".join(failures)
        return f"(nothing established for this question; {failed} failed)"
    return "(nothing established)"


def status_display(status: str) -> str:
    """Human label for a corpus status; never upgrades the underlying value."""
    return _STATUS_LABEL.get(status, status)


def format_references_zone(hits: Sequence[Mapping[str, Any]]) -> str:
    """Corpus References body from literature_search hits (not model text)."""
    if not hits:
        return ""
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for h in hits:
        name = str(h.get("name", ""))
        lean = str(h.get("lean_name", ""))
        status = str(h.get("status", ""))
        key = (name, lean)
        if key in seen:
            continue
        seen.add(key)
        prov = str(h.get("provenance", ""))
        short = lean.rsplit(".", 1)[-1] if lean else ""
        label = f"{name} / {short}" if short and short != name else name
        line = f"{label} — {status_display(status)}"
        if prov:
            line += f" [{prov}]"
        lines.append(line)
    return "\n".join(lines)


def format_grounded_answer(
    *,
    commentary: str,
    claims: Sequence[Claim] = (),
    failures: Sequence[str] = (),
    references: Sequence[Mapping[str, Any]] = (),
) -> str:
    """Final answer: Established → optional References → Commentary."""
    established = format_established_zone(claims, failures)
    prose = commentary_prose_only(commentary) or "(no commentary)"
    parts = [f"Established (ledger):\n{established}"]
    refs_body = format_references_zone(references)
    if refs_body:
        parts.append(f"References (corpus):\n{refs_body}")
    parts.append(f"Commentary:\n{prose}")
    return "\n\n".join(parts)
