"""Answer grounding: system-prompt rules + Established/Commentary presentation.

Konigsberg's hard trust boundary is the ledger. Prose is commentary. These
helpers reduce the chance of misleading final answers but do not make free-text
math claims mechanically verifiable — only Claims carry trust.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from .ledger import Claim

GROUNDING_SYSTEM_PROMPT = """\
You are Konigsberg's graph-theory research assistant. Tools mint Claims into an \
epistemic ledger; the ledger is the only trusted record of results.

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
5. Your output is commentary prose only. Do not restate established results or \
print a ledger; the harness renders the Established (ledger) zone and the \
authoritative ledger view. Do not emit markdown sections titled Established, \
Commentary, or /ledger, and do not print ledger tables.
6. A bare "/ledger" inside a user sentence is not a slash command (commands are \
lines that start with /). Do not emulate /ledger in your text — tell the user \
to run /ledger themselves if they want the harness ledger view.

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

The user-facing answer is rendered in two zones by the harness (Established from \
the ledger, Commentary from your prose). Keep commentary honest: if nothing was \
established, say so — do not invent a verdict.
"""

# Model sometimes shadow-renders harness zones; strip those before we wrap.
_SHADOW_SECTION = re.compile(
    r"(?ms)^(?:---+\s*)?##\s*\*?\*?/?\s*(?:Established|/ledger)\*?\*?"
    r".*?(?=^(?:---+\s*)?##\s|\Z)"
)
_COMMENTARY_HEADER = re.compile(
    r"(?m)^(?:---+\s*)?##\s*\*?\*?Commentary\*?\*?\s*\n+"
)


def commentary_prose_only(text: str) -> str:
    """Keep model output as prose; drop emulated Established / ledger sections."""
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


def format_grounded_answer(
    *,
    commentary: str,
    claims: Sequence[Claim] = (),
    failures: Sequence[str] = (),
) -> str:
    """Two-zone final answer: Established (ledger) then Commentary (model prose)."""
    established = format_established_zone(claims, failures)
    prose = commentary_prose_only(commentary) or "(no commentary)"
    return (
        f"Established (ledger):\n{established}\n\n"
        f"Commentary:\n{prose}"
    )
