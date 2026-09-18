"""Referee gate — adversarial review at the promotion boundary only.

Fail-closed: promotion requires a real adversarial ``accept``. Heuristic-only
review returns ``no-automated-issues``; model failure returns ``unavailable``.
Neither unblocks ``/promote``.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from .ledger import Claim
from .models import Model

Recommendation = Literal[
    "accept",
    "no-automated-issues",
    "unavailable",
    "minor",
    "major",
    "reject",
]
CheckVerdict = Literal["pass", "fail", "minor", "na"]


class CheckKind(str, Enum):
    DEFINITION_FAITHFULNESS = "definition_predicate_faithfulness"
    EMPIRICAL_CROSS_CHECK = "empirical_cross_check"
    HYPOTHESIS_NECESSITY = "hypothesis_necessity"
    VACUITY_TRIVIALITY = "vacuity_triviality"
    SCOPE_CREEP = "scope_creep"
    SIGNIFICANCE = "significance_novelty"


REFEREE_PROMPT = """\
You are the Konigsberg REFEREE — a distinct adversarial reviewer, not the \
producer. Break-it-fairly: try to falsify or weaken the artifact before it \
becomes a durable Literature entry.

Hard rules:
1. Compute objections with tools — never assert without tool backing. Prefer \
make_graph / blow_up / independent_hitting_set / clique_number / max_degree / \
literature_search / lean_search / lean_check.
2. The Lean kernel checks the proof, not the meaning — that meaning gap is \
YOUR beat. A kernel-valid proof of the wrong predicate is a Major issue.
3. Fair and constructive: credit what is right; propose corrected statements.
4. Honest limit: you share blind spots with the producer. Tool-grounded checks \
are the robust core; kernel + tools stay final authority.
5. Do NOT mint Claims and do NOT call lean_add_to_library.

Checks (run those that apply; ``na`` must be justified structurally):
(1) Definition/predicate faithfulness — bespoke definitions (sProdF, custom \
predicates) vs intended standard notions; Major if unbridged.
(2) Empirical cross-check — if a tool can compute the property, test a \
discriminating instance; disagreement ⇒ Major.
(3) Hypothesis necessity — strip each hypothesis; counterexample ⇒ load-bearing.
(4) Vacuity/triviality — non-vacuity witness? trivially true?
(5) Scope-creep + significance/novelty — universal-from-sweep, unpinned \
constants; literature_search for novelty.

Final answer MUST be a single JSON object (no markdown fences):
  "established": [string],
  "major_issues": [string],
  "minor_issues": [string],
  "suggested_revision": string,
  "recommendation": "accept" | "minor" | "major" | "reject",
  "checks": [{"kind": string, "verdict": "pass"|"fail"|"minor"|"na", \
"detail": string, "tool": string, "na_justification": string}]

``recommendation`` is the promotion decision, not a summary of whether any \
caveat exists. Use ``accept`` when the statement is ready to promote; \
``minor_issues`` on an accept are non-blocking notes (folklore, docstring \
clarity already in the Notes, etc.). Use ``minor`` only when the artifact \
must be revised before promotion. Use ``major``/``reject`` for meaning gaps \
or false claims.
"""


# Known standard notions → bespoke-name hints (not exhaustive; heuristic).
_STANDARD_NOTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("strong product", re.compile(r"strong\s+product", re.IGNORECASE)),
    ("lexicographic product", re.compile(r"lex(?:icographic)?\s+product", re.IGNORECASE)),
    ("maximum-clique hitting", re.compile(r"(?:max(?:imum)?\s+)?clique.*hit", re.IGNORECASE)),
    ("list coloring", re.compile(r"list[\s-]?color", re.IGNORECASE)),
    ("choosability", re.compile(r"choosabilit", re.IGNORECASE)),
]

# Whole-identifier camelCase (sProdF) or PascalCase with ≥2 capitals (KCritical).
# Applied to ident tokens only — a search over the raw string slices PascalCase
# interiors (CompleteGraphKCritical → ompleteGraphKCritical).
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
_CAMEL_IDENT_RE = re.compile(r"[a-z]+[A-Z][A-Za-z0-9]*\Z")
_PASCAL_IDENT_RE = re.compile(r"[A-Z][a-z0-9]*[A-Z][A-Za-z0-9]*\Z")
_STDLIB_NAMES = {
    "SimpleGraph",
    "Finset",
    "Nat",
    "Int",
    "Bool",
    "Graph",
    "List",
    "Option",
    "True",
    "False",
    "Prop",
    "Type",
    "Sort",
    "Classical",
    "Quot",
    "Colorable",
    "ListColorable",
    "Mathlib",
    "Konigsberg",
    "Lean",
    "completeGraph",
}
_BRIDGE_MARKERS = re.compile(
    r"(?:=\s*(?:Mathlib|the\s+standard)|def_eq|same\s+as|equal\s+to\s+(?:the\s+)?"
    r"(?:standard|Mathlib|intended)|bridging\s+lemma|shown\s+equal)",
    re.IGNORECASE,
)
_HYPOTHESIS_MARKERS = re.compile(
    r"\b(triangle[\s-]?free|bipartite|connected|simple|finite|non[\s-]?empty|"
    r"Δ\s*[≥>=]|ω\s*[≥>=]|for all|∀)\b",
    re.IGNORECASE,
)
_VACUOUS_PATTERNS = re.compile(
    r"\b(no\s+vertices|zero\s+vertices|empty\s+(?:graph|vertex\s+set)|"
    r"0\s+vertices|vacuous|uninhabited|False\s*→|False\s*->|"
    r"impossible\s+hypoth)",
    re.IGNORECASE,
)
# Minimal-counterexample / contradiction lemmas: conclusion is False.
_FALSE_CONCLUSION = re.compile(
    r"(?:⇒|→|->)\s*False\b|:\s*[^.]*?(?:⇒|→|->)\s*False\b",
    re.IGNORECASE,
)
_SAT_WITNESS_MARKERS = re.compile(
    r"\b(SanityChecks|satisfiab|non[\s-]?vacuous\s+witness|non[\s-]?vacuity|"
    r"inhabited\s+instance|completeGraph_kCritical|"
    r"example\s*:|witness(?:ed|ing)?\s+hypoth)\b",
    re.IGNORECASE,
)
_TRIVIAL_PATTERNS = re.compile(
    r"\b(True\s*:=\s*trivial|True\s*↔\s*True|0\s*=\s*0|theorem\s+\w+\s*:\s*True\b)",
    re.IGNORECASE,
)


class RefereeUnavailable(RuntimeError):
    """Adversarial referee could not run — promotion must stay blocked."""


@dataclass(frozen=True)
class CheckFinding:
    kind: str
    verdict: CheckVerdict
    detail: str
    tool: str = ""
    na_justification: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class RefereeReport:
    """Structured referee output. ``allows_promotion`` is the write-back gate."""

    recommendation: Recommendation
    established: tuple[str, ...] = ()
    major_issues: tuple[str, ...] = ()
    minor_issues: tuple[str, ...] = ()
    suggested_revision: str = ""
    checks: tuple[CheckFinding, ...] = ()
    raw_text: str = ""
    claim_statement: str = ""
    adversarial_review_ran: bool = False
    review_unavailable_reason: str = ""

    def allows_promotion(self) -> bool:
        return (
            self.recommendation == "accept"
            and self.adversarial_review_ran
            and not self.major_issues
        )

    def render(self) -> str:
        if self.recommendation == "unavailable":
            lines = [
                "REFEREE UNAVAILABLE — not vetted; promotion blocked.",
                f"Reason: {self.review_unavailable_reason or '(unknown)'}",
            ]
        elif self.recommendation == "no-automated-issues":
            lines = [
                "Recommendation: no-automated-issues (NOT adversarially reviewed)",
                "Promotion blocked — run a live adversarial referee before /promote.",
            ]
        else:
            mode = (
                "full adversarial + heuristic"
                if self.adversarial_review_ran
                else "heuristic only"
            )
            lines = [
                f"Recommendation: {self.recommendation}",
                f"Review mode: {mode}",
            ]
        if self.established:
            lines.append("Established:")
            lines.extend(f"  - {x}" for x in self.established)
        if self.major_issues:
            lines.append("Major issues:")
            lines.extend(f"  - {x}" for x in self.major_issues)
        if self.minor_issues:
            lines.append("Minor issues:")
            lines.extend(f"  - {x}" for x in self.minor_issues)
        if self.suggested_revision:
            lines.append(f"Suggested revision:\n  {self.suggested_revision}")
        if self.checks:
            lines.append("Checks:")
            for c in self.checks:
                tool = f" [{c.tool}]" if c.tool else ""
                na = f" (na: {c.na_justification})" if c.verdict == "na" else ""
                lines.append(f"  - ({c.kind}) {c.verdict}{tool}{na}: {c.detail}")
        return "\n".join(lines)

    def to_notes_section(self) -> str:
        return "## Referee report\n\n```\n" + self.render() + "\n```\n"

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation": self.recommendation,
            "established": list(self.established),
            "major_issues": list(self.major_issues),
            "minor_issues": list(self.minor_issues),
            "suggested_revision": self.suggested_revision,
            "checks": [c.to_dict() for c in self.checks],
            "claim_statement": self.claim_statement,
            "adversarial_review_ran": self.adversarial_review_ran,
            "review_unavailable_reason": self.review_unavailable_reason,
            "allows_promotion": self.allows_promotion(),
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], *, claim_statement: str = ""
    ) -> RefereeReport:
        checks = tuple(
            CheckFinding(
                kind=str(c.get("kind", "")),
                verdict=c.get("verdict", "na"),  # type: ignore[arg-type]
                detail=str(c.get("detail", "")),
                tool=str(c.get("tool", "")),
                na_justification=str(c.get("na_justification", "")),
            )
            for c in (data.get("checks") or [])
            if isinstance(c, dict)
        )
        rec = str(data.get("recommendation", "reject"))
        allowed = (
            "accept",
            "no-automated-issues",
            "unavailable",
            "minor",
            "major",
            "reject",
        )
        if rec not in allowed:
            rec = "reject"
        return cls(
            recommendation=rec,  # type: ignore[arg-type]
            established=tuple(str(x) for x in data.get("established") or ()),
            major_issues=tuple(str(x) for x in data.get("major_issues") or ()),
            minor_issues=tuple(str(x) for x in data.get("minor_issues") or ()),
            suggested_revision=str(data.get("suggested_revision") or ""),
            checks=checks,
            raw_text=json.dumps(data, indent=2),
            claim_statement=claim_statement or str(data.get("claim_statement") or ""),
            adversarial_review_ran=bool(data.get("adversarial_review_ran")),
            review_unavailable_reason=str(data.get("review_unavailable_reason") or ""),
        )


def parse_referee_report(text: str, *, claim_statement: str = "") -> RefereeReport:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return RefereeReport(
            recommendation="reject",
            major_issues=("referee output was not structured JSON",),
            raw_text=text,
            claim_statement=claim_statement,
        )
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return RefereeReport(
            recommendation="reject",
            major_issues=("referee JSON failed to parse",),
            raw_text=text,
            claim_statement=claim_statement,
        )
    if not isinstance(data, dict):
        return RefereeReport(
            recommendation="reject",
            major_issues=("referee JSON was not an object",),
            raw_text=text,
            claim_statement=claim_statement,
        )
    report = RefereeReport.from_dict(data, claim_statement=claim_statement)
    # Parsed from live adversarial pass.
    return RefereeReport(
        recommendation=report.recommendation,
        established=report.established,
        major_issues=report.major_issues,
        minor_issues=report.minor_issues,
        suggested_revision=report.suggested_revision,
        checks=report.checks,
        raw_text=report.raw_text,
        claim_statement=report.claim_statement,
        adversarial_review_ran=True,
    )


def _graph6_from_claim(claim: Claim) -> str | None:
    m = re.search(r"graph6=(\S+)", claim.statement)
    return m.group(1) if m else None


def _extract_bespoke_definitions(statement: str) -> set[str]:
    """Camel/Pascal identifiers, as whole tokens — never interior slices."""
    found: set[str] = set()
    for ident in _IDENT_RE.findall(statement):
        if ident in _STDLIB_NAMES or len(ident) < 3:
            continue
        if _CAMEL_IDENT_RE.match(ident) or _PASCAL_IDENT_RE.match(ident):
            found.add(ident)
    return found


def _intended_standard_notions(statement: str) -> list[str]:
    return [name for name, pat in _STANDARD_NOTION_PATTERNS if pat.search(statement)]


def check_definition_faithfulness(
    statement: str, *, lean_type: str | None = None
) -> CheckFinding:
    """Check 1: bespoke defs vs intended standard notions — unbridged ⇒ Major.

    Prefer the Lean type/docstring text when available; claim.statement is a fallback.
    """
    text = "\n".join(p for p in (statement, lean_type) if p) or statement
    bespoke = _extract_bespoke_definitions(text)
    intended = _intended_standard_notions(text)
    if not bespoke:
        return CheckFinding(
            CheckKind.DEFINITION_FAITHFULNESS.value,
            "na",
            "no bespoke definitions detected in claim text",
            na_justification="claim uses no self-authored definition names",
        )
    if intended and not _BRIDGE_MARKERS.search(text):
        return CheckFinding(
            CheckKind.DEFINITION_FAITHFULNESS.value,
            "fail",
            f"bespoke definitions {sorted(bespoke)} used while claim is about "
            f"{intended} — no bridging lemma (= standard/Mathlib) cited",
            tool="lean_search",
        )
    if bespoke:
        return CheckFinding(
            CheckKind.DEFINITION_FAITHFULNESS.value,
            "pass",
            f"bespoke definitions {sorted(bespoke)} present — names only; no "
            "unmatched standard-notion claim (meaning is for the adversarial pass)",
        )
    return CheckFinding(
        CheckKind.DEFINITION_FAITHFULNESS.value,
        "na",
        "no bespoke definitions detected",
        na_justification="claim uses no self-authored definition names",
    )


def _empirical_hitting_crosscheck(statement: str) -> CheckFinding | None:
    """Hitting ⟺ bipartite instance of empirical cross-check."""
    s = statement.lower()
    if "bipartite" not in s:
        return None
    if not any(k in s for k in ("hit", "hitting", "maximum clique", "max clique")):
        return None

    from .tools import fundamentals_tools as ft

    k3 = ft.make_graph(kind="complete", n=3)
    g6 = _graph6_from_claim(k3)
    if not g6:
        return CheckFinding(
            CheckKind.EMPIRICAL_CROSS_CHECK.value,
            "na",
            "could not build K₃ for hitting cross-check",
            na_justification="make_graph failed",
        )
    blown = ft.blow_up(g6, 2, clique=True)
    g6b = _graph6_from_claim(blown)
    if not g6b:
        return CheckFinding(
            CheckKind.EMPIRICAL_CROSS_CHECK.value,
            "na",
            "could not blow up K₃",
            na_justification="blow_up failed",
        )
    hit = ft.independent_hitting_set(g6b)
    holds = "HOLDS" in hit.statement.upper()
    triangle_free = any(
        t in s for t in ("triangle-free", "triangle free", "triangle_free")
    )

    if not triangle_free and holds:
        return CheckFinding(
            CheckKind.EMPIRICAL_CROSS_CHECK.value,
            "fail",
            "K₃[K₂]: independent_hitting_set HOLDS while K₃ is non-bipartite — "
            "theorem predicate ≠ real maximum-clique hitting property",
            tool="independent_hitting_set",
        )
    if triangle_free and holds:
        return CheckFinding(
            CheckKind.EMPIRICAL_CROSS_CHECK.value,
            "pass",
            "K₃[K₂] discriminating instance consistent with triangle-free scope",
            tool="independent_hitting_set",
        )
    return CheckFinding(
        CheckKind.EMPIRICAL_CROSS_CHECK.value,
        "fail",
        "hitting/bipartite claim failed empirical cross-check on K₃[K₂]",
        tool="independent_hitting_set",
    )


def check_empirical_cross_check(statement: str) -> CheckFinding:
    """Check 2: tool-computable property vs theorem on discriminating instance."""
    hitting = _empirical_hitting_crosscheck(statement)
    if hitting is not None:
        return hitting
    return CheckFinding(
        CheckKind.EMPIRICAL_CROSS_CHECK.value,
        "na",
        "no registered empirical tool maps to this claim's predicate",
        na_justification="property not matched to independent_hitting_set or other tools",
    )


def check_hypothesis_necessity(
    statement: str, *, lean_type: str | None = None
) -> CheckFinding:
    """Check 3: strip hypotheses and seek counterexamples.

    Prefer Lean type text when available for binder/hypothesis detection.
    """
    text = lean_type or statement
    s = text.lower()

    # Hitting ⟺ bipartite without triangle-free: missing load-bearing hypothesis.
    if (
        "bipartite" in s
        and any(k in s for k in ("hit", "hitting", "maximum clique", "max clique"))
        and not re.search(r"triangle[\s-]?free", text, re.IGNORECASE)
    ):
        cross = _empirical_hitting_crosscheck(statement)
        if cross is not None and cross.verdict == "fail":
            return CheckFinding(
                CheckKind.HYPOTHESIS_NECESSITY.value,
                "fail",
                "missing triangle-free (or similar) hypothesis — claim false without it "
                "(K₃[K₂] witness)",
                tool="independent_hitting_set",
            )

    hypotheses = _HYPOTHESIS_MARKERS.findall(text)
    if not hypotheses and not _has_binder_chain(text):
        return CheckFinding(
            CheckKind.HYPOTHESIS_NECESSITY.value,
            "na",
            "no identifiable hypotheses to test",
            na_justification="claim has no parseable conditional hypotheses",
        )

    # Triangle-free necessity via K₃ cross-check when hitting claim present.
    if re.search(r"triangle[\s-]?free", text, re.IGNORECASE):
        stripped = re.sub(r"triangle[\s-]?free", "", text, flags=re.IGNORECASE)
        if stripped != text:
            cross = _empirical_hitting_crosscheck(stripped)
            if cross is not None and cross.verdict == "fail":
                return CheckFinding(
                    CheckKind.HYPOTHESIS_NECESSITY.value,
                    "pass",
                    "stripping triangle-free yields false instance on K₃[K₂] — "
                    "hypothesis is load-bearing",
                    tool="independent_hitting_set",
                )

    # Unqualified universal hitting: C₅ counterexample.
    if (
        any(k in s for k in ("every graph", "all graphs", "for all", "∀"))
        and any(k in s for k in ("hit", "hitting"))
        and "bipartite" not in s
    ):
        from .tools import fundamentals_tools as ft

        c5 = ft.make_graph(kind="cycle", n=5)
        g6 = _graph6_from_claim(c5)
        if g6:
            hit = ft.independent_hitting_set(g6)
            if "FAILS" in hit.statement.upper() or "NO independent" in hit.statement:
                return CheckFinding(
                    CheckKind.HYPOTHESIS_NECESSITY.value,
                    "fail",
                    "unconditional hitting claim false on C₅ — missing necessary "
                    "hypotheses",
                    tool="independent_hitting_set",
                )

    labels = hypotheses[:5] or ["binder chain"]
    return CheckFinding(
        CheckKind.HYPOTHESIS_NECESSITY.value,
        "pass",
        f"tested hypotheses {labels} — no counterexample found by heuristics",
    )


def check_vacuity_triviality(
    statement: str, *, lean_type: str | None = None, notes: str | None = None
) -> CheckFinding:
    """Check 4: vacuous hypotheses or trivially true statements.

    Claims whose conclusion is ``False`` (minimal-counterexample lemmas) are
    worthless if the hypotheses are jointly unsatisfiable. Heuristic cannot prove
    satisfiability ⇒ **block** unless a satisfiability witness is present
    (SanityChecks / inhabited instance / explicit witness language).
    Literature Notes are consulted only for that witness, not for other patterns
    (they mention "vacuous" SanityChecks / HIT tags as documentation).
    """
    claim = "\n".join(p for p in (statement, lean_type) if p) or statement
    witness = "\n".join(p for p in (statement, lean_type, notes) if p)
    if _FALSE_CONCLUSION.search(claim) and not _SAT_WITNESS_MARKERS.search(witness):
        return CheckFinding(
            CheckKind.VACUITY_TRIVIALITY.value,
            "fail",
            "conclusion is False (⇒ False) without a satisfiability witness for "
            "the hypotheses — block until SanityChecks / inhabited instance exists",
        )
    if _VACUOUS_PATTERNS.search(claim):
        return CheckFinding(
            CheckKind.VACUITY_TRIVIALITY.value,
            "fail",
            "vacuous or uninhabited hypothesis detected — statement may be trivial",
        )
    if _TRIVIAL_PATTERNS.search(claim):
        return CheckFinding(
            CheckKind.VACUITY_TRIVIALITY.value,
            "fail",
            "trivially true statement detected (True/trivial/0=0)",
        )
    if re.search(r"\bfor all\b.*\bwhere False\b", claim, re.IGNORECASE):
        return CheckFinding(
            CheckKind.VACUITY_TRIVIALITY.value,
            "fail",
            "hypothesis 'where False' makes statement vacuous",
        )
    return CheckFinding(
        CheckKind.VACUITY_TRIVIALITY.value,
        "pass",
        "no vacuity/triviality heuristic fired",
    )


def check_scope_creep(
    statement: str, ledger_claims: tuple[Claim, ...] = ()
) -> CheckFinding:
    """Check 5a: universal-from-sweep, constant conflation."""
    s = statement.lower()
    issues: list[str] = []
    if re.search(r"2/3|⅔", s) and re.search(r"3/4|¾", s) and "rabern" in s:
        issues.append("possible ⅔/¾ constant conflation (King vs Rabern)")
    if re.search(r"\bfor all\b", s) and any(
        "n<=" in c.statement.lower() or "n≤" in c.statement for c in ledger_claims
    ):
        issues.append("universal 'for all' adjacent to bounded enumeration Claims")
    if re.search(r"\bfor all graphs\b", s) and re.search(r"\bn\s*[≤<=]\s*\d", s):
        issues.append("universal claim may be inferred from bounded sweep")
    if not issues:
        return CheckFinding(
            CheckKind.SCOPE_CREEP.value,
            "pass",
            "no scope-creep heuristic fired",
        )
    return CheckFinding(
        CheckKind.SCOPE_CREEP.value,
        "fail",
        "; ".join(issues),
    )


def check_significance(statement: str, *, registry: Any | None = None) -> CheckFinding:
    """Check 5b: literature novelty calibration."""
    names = set(registry.names()) if registry is not None else set()
    if "literature_search" not in names:
        return CheckFinding(
            CheckKind.SIGNIFICANCE.value,
            "na",
            "literature_search unavailable",
            na_justification="registry has no literature_search",
        )
    tokens = re.findall(r"[A-Za-z]{4,}", statement)
    query = " ".join(tokens[:6]) or "graph coloring"
    try:
        hits = registry.dispatch("literature_search", {"query": query})
    except Exception as e:  # noqa: BLE001
        return CheckFinding(
            CheckKind.SIGNIFICANCE.value,
            "na",
            f"literature_search failed: {e}",
            na_justification="tool error",
            tool="literature_search",
        )
    n = len(hits) if isinstance(hits, list) else 0
    return CheckFinding(
        CheckKind.SIGNIFICANCE.value,
        "pass",
        f"literature_search({query!r}) → {n} hit(s); true≠new — calibrate novelty",
        tool="literature_search",
    )


def _has_binder_chain(text: str) -> bool:
    """True when the Lean type has ∀ / a ``→ … →`` hypothesis chain."""
    if re.search(r"(?:∀|forall)\b", text, re.IGNORECASE):
        return True
    return len(re.findall(r"→|->|⇒", text)) >= 1


def _fetch_lean_context(repl: Any, lean_name: str) -> str | None:
    """``#check`` type plus ``#print axioms`` — not Notes (those fire HIT/vacuous false positives)."""
    chunks: list[str] = []
    try:
        state = repl.send(f"#check {lean_name}", commit=False)
        text = "\n".join([*state.infos, *state.errors]).strip()
        if text:
            chunks.append(text)
    except Exception:  # noqa: BLE001, S110
        pass
    printer = getattr(repl, "print_axioms", None)
    if callable(printer):
        try:
            axioms = printer(lean_name)
            if axioms:
                chunks.append("axioms: " + ", ".join(str(a) for a in axioms))
        except Exception:  # noqa: BLE001, S110
            pass
    else:
        try:
            state = repl.send(f"#print axioms {lean_name}", commit=False)
            text = "\n".join(state.infos).strip()
            if text:
                chunks.append(text)
        except Exception:  # noqa: BLE001, S110
            pass
    return "\n".join(chunks) or None


def _literature_notes(lean_name: str) -> str | None:
    """Notes.md next to a Literature declaration, if any — sat-witness text."""
    parts = lean_name.split(".")
    if len(parts) < 4 or parts[:2] != ["Konigsberg", "Literature"]:
        return None
    path = (
        Path(__file__).resolve().parents[2]
        / "formal"
        / "Konigsberg"
        / Path(*parts[1:-1])
        / "Notes.md"
    )
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _fetch_lean_type(repl: Any, lean_name: str) -> str | None:
    """Best-effort Lean type + axiom dump for a declared name."""
    return _fetch_lean_context(repl, lean_name)


def run_tool_grounded_checks(
    statement: str,
    *,
    registry: Any | None = None,
    ledger_claims: tuple[Claim, ...] = (),
    repl: Any | None = None,
    lean_name: str | None = None,
) -> tuple[CheckFinding, ...]:
    """Run claim-agnostic heuristic checks (no LLM).

    When ``repl`` is available, prefer the Lean type of ``lean_name`` (or the
    statement if it looks like a decl name) over the claim string for
    faithfulness / hypothesis / vacuity checks.
    """
    lean_type: str | None = None
    notes: str | None = None
    name = lean_name
    if name is None and re.fullmatch(r"[A-Za-z0-9_'.]+", statement.strip()):
        name = statement.strip()
    if repl is not None and name:
        lean_type = _fetch_lean_type(repl, name)
    if name:
        notes = _literature_notes(name)

    return (
        check_definition_faithfulness(statement, lean_type=lean_type),
        check_empirical_cross_check(statement),
        check_hypothesis_necessity(statement, lean_type=lean_type),
        check_vacuity_triviality(statement, lean_type=lean_type, notes=notes),
        check_scope_creep(statement, ledger_claims),
        check_significance(statement, registry=registry),
    )


_MAJOR_KINDS = {
    CheckKind.DEFINITION_FAITHFULNESS.value,
    CheckKind.EMPIRICAL_CROSS_CHECK.value,
    CheckKind.HYPOTHESIS_NECESSITY.value,
    CheckKind.VACUITY_TRIVIALITY.value,
}


def _issues_from_checks(
    checks: tuple[CheckFinding, ...],
) -> tuple[list[str], list[str], list[str]]:
    major = [c.detail for c in checks if c.verdict == "fail" and c.kind in _MAJOR_KINDS]
    minor = [
        c.detail
        for c in checks
        if c.verdict in ("fail", "minor") and c.kind not in _MAJOR_KINDS
    ]
    minor += [c.detail for c in checks if c.verdict == "minor"]
    established = [c.detail for c in checks if c.verdict == "pass"]
    return major, minor, established


def _merge_reports(
    statement: str,
    checks: tuple[CheckFinding, ...],
    *,
    model_report: RefereeReport | None = None,
    adversarial_review_ran: bool = False,
    unavailable_reason: str = "",
) -> RefereeReport:
    major, minor, established = _issues_from_checks(checks)
    suggested = ""
    if any(
        c.kind == CheckKind.EMPIRICAL_CROSS_CHECK.value and c.verdict == "fail"
        for c in checks
    ):
        suggested = (
            "Restrict to triangle-free H: for triangle-free H and r≥1, H[Kᵣ] "
            "admits an independent set meeting every maximum clique ⟺ H is bipartite."
        )

    merged_checks: tuple[CheckFinding, ...] = checks
    if model_report is not None:
        major = list(dict.fromkeys([*major, *model_report.major_issues]))
        minor = list(dict.fromkeys([*minor, *model_report.minor_issues]))
        established = list(dict.fromkeys([*established, *model_report.established]))
        if model_report.suggested_revision:
            suggested = model_report.suggested_revision
        merged_checks = (*checks, *model_report.checks)

    if unavailable_reason:
        return RefereeReport(
            recommendation="unavailable",
            major_issues=tuple(major),
            minor_issues=tuple(minor),
            suggested_revision=suggested,
            checks=merged_checks,
            claim_statement=statement,
            adversarial_review_ran=False,
            review_unavailable_reason=unavailable_reason,
        )

    if major:
        rec: Recommendation = "major"
    elif adversarial_review_ran:
        rec = "accept"
        if model_report is not None:
            mrec = model_report.recommendation
            if mrec in ("minor", "major", "reject"):
                rec = mrec  # type: ignore[assignment]
    elif minor:
        rec = "minor"
    else:
        rec = "no-automated-issues"

    return RefereeReport(
        recommendation=rec,
        established=tuple(established),
        major_issues=tuple(major),
        minor_issues=tuple(minor),
        suggested_revision=suggested,
        checks=merged_checks,
        claim_statement=statement,
        raw_text=model_report.raw_text if model_report else "",
        adversarial_review_ran=adversarial_review_ran,
    )


def build_referee_model() -> Model:
    """Distinct live-model instance with REFEREE_PROMPT (no temperature — many models reject it)."""
    from .models import build_live_model

    return build_live_model(system_prompt=REFEREE_PROMPT, temperature=None)


def run_referee(
    claim: Claim | str,
    *,
    registry: Any | None = None,
    model: Model | None = None,
    ledger_claims: tuple[Claim, ...] = (),
    max_steps: int = 12,
    require_adversarial: bool = False,
    repl: Any | None = None,
) -> RefereeReport:
    """Run heuristic checks + optional adversarial model pass.

    Fail-closed:
    - No model / heuristic only → ``no-automated-issues`` (blocks promotion).
    - Model error → ``unavailable`` (blocks promotion).
    - ``accept`` only when adversarial pass ran and no Major issues remain.
    """
    statement = claim.statement if isinstance(claim, Claim) else str(claim)
    lean_name = None
    if isinstance(claim, Claim) and claim.provenance.tool == "lean_prove":
        lean_name = claim.statement
    checks = run_tool_grounded_checks(
        statement,
        registry=registry,
        ledger_claims=ledger_claims,
        repl=repl,
        lean_name=lean_name,
    )

    if model is None:
        return _merge_reports(statement, checks, adversarial_review_ran=False)

    if registry is None:
        return _merge_reports(
            statement,
            checks,
            adversarial_review_ran=False,
            unavailable_reason="registry required for adversarial referee",
        )

    try:
        model_report = _referee_agent_pass(
            statement,
            registry=registry,
            model=model,
            ledger_claims=ledger_claims,
            prior_checks=checks,
            max_steps=max_steps,
        )
    except RefereeUnavailable as e:
        return _merge_reports(
            statement,
            checks,
            unavailable_reason=str(e),
        )
    except Exception as e:  # noqa: BLE001
        return _merge_reports(
            statement,
            checks,
            unavailable_reason=f"model error: {type(e).__name__}: {e}",
        )

    return _merge_reports(
        statement,
        checks,
        model_report=model_report,
        adversarial_review_ran=True,
    )


_JSON_PARSE_FAILURES = frozenset(
    {
        "referee output was not structured JSON",
        "referee JSON failed to parse",
        "referee JSON was not an object",
    }
)


def _parsed_json_report(text: str, statement: str) -> RefereeReport | None:
    """Return a structured report, or None if the model did not emit JSON."""
    if not text.strip():
        return None
    parsed = parse_referee_report(text, claim_statement=statement)
    if (
        parsed.recommendation == "reject"
        and parsed.major_issues
        and all(m in _JSON_PARSE_FAILURES for m in parsed.major_issues)
        and not parsed.established
        and not parsed.checks
    ):
        return None
    return parsed


def _force_referee_json(model: Model, history: list) -> str:
    """One final no-tools turn: emit only the JSON report from gathered context."""
    from .models import AssistantText, Tier, UserMsg

    history = list(history)
    history.append(
        UserMsg(
            "Stop calling tools. Emit ONLY the final JSON referee report now, "
            "using everything you have gathered. No prose outside the JSON object."
        )
    )
    turn = model.respond(history, tools=[], tier=Tier.FRONTIER)
    if isinstance(turn, AssistantText):
        return turn.text
    return ""


def _referee_agent_pass(
    statement: str,
    *,
    registry: Any,
    model: Model,
    ledger_claims: tuple[Claim, ...],
    prior_checks: tuple[CheckFinding, ...],
    max_steps: int,
) -> RefereeReport:
    from .agent import Agent, AgentConfig

    prev = getattr(model, "system_prompt", None)
    if prev is not None:
        model.system_prompt = REFEREE_PROMPT
    try:
        ledger_txt = "\n".join(c.render() for c in ledger_claims) or "(empty)"
        checks_txt = "\n".join(
            f"- {c.kind}: {c.verdict} — {c.detail}" for c in prior_checks
        )
        brief = (
            "Referee the following Claim for possible Literature promotion.\n\n"
            f"CLAIM:\n{statement}\n\n"
            f"SESSION LEDGER:\n{ledger_txt}\n\n"
            f"PRECOMPUTED TOOL CHECKS:\n{checks_txt}\n\n"
            "Run further tool checks as needed, then emit the final JSON report."
        )
        agent = Agent(registry, model, AgentConfig(max_steps=max_steps))
        try:
            result = agent.run(brief)
        except Exception as e:
            raise RefereeUnavailable(
                f"model error: {type(e).__name__}: {e}"
            ) from e
        text = result.commentary or result.final or ""
        parsed = _parsed_json_report(text, statement)
        if parsed is not None:
            return parsed
        # Step exhaustion / non-JSON prose: force one no-tools report turn.
        sess = result.session
        hist = list(sess.history) if sess is not None else []
        try:
            text = _force_referee_json(model, hist)
        except Exception as e:
            raise RefereeUnavailable(
                "referee exhausted steps before emitting report; "
                f"forced final turn failed: {type(e).__name__}: {e}"
            ) from e
        parsed = _parsed_json_report(text, statement)
        if parsed is None:
            if not text.strip():
                raise RefereeUnavailable(
                    "referee exhausted steps before emitting report"
                )
            raise RefereeUnavailable(
                "adversarial referee did not return valid JSON"
            )
        return parsed
    finally:
        if prev is not None:
            model.system_prompt = prev


# --- Self-test corpus (ci/referee_self_test.py) --------------------------------

PLANT_UNCORRECTED_MAIN = (
    "For all graphs H and r≥1: H[K_r] admits an independent set meeting every "
    "maximum clique if and only if H is bipartite."
)
PLANT_SPRODF = (
    "Theorem: choosability of the strong product G × H is characterized via "
    "sProdF(G,H) and lProdF(G,H) — our custom product definitions. "
    "Lean proof uses sProdF/lProdF without showing sProdF equals the standard "
    "Mathlib strong product."
)
PLANT_VACUOUS = (
    "Lemma: for all graphs G with zero vertices (empty vertex set), every "
    "property P holds vacuously. Proof: True := trivial."
)
PLANT_FALSE_CONCLUSION = (
    "Theorem: ∀ G, KCritical G 9 → FChoosableZ G f → False. "
    "Load-bearing hypotheses have no exhibited model."
)
PLANT_CLEAN = (
    "For triangle-free H and r≥1: H[K_r] admits an independent set meeting every "
    "maximum clique if and only if H is bipartite."
)


# Back-compat aliases for tests
cross_check_hitting_bipartite = check_empirical_cross_check


__all__ = [
    "PLANT_CLEAN",
    "PLANT_FALSE_CONCLUSION",
    "PLANT_SPRODF",
    "PLANT_UNCORRECTED_MAIN",
    "PLANT_VACUOUS",
    "REFEREE_PROMPT",
    "CheckFinding",
    "CheckKind",
    "RefereeReport",
    "RefereeUnavailable",
    "build_referee_model",
    "check_definition_faithfulness",
    "check_empirical_cross_check",
    "check_hypothesis_necessity",
    "check_vacuity_triviality",
    "cross_check_hitting_bipartite",
    "parse_referee_report",
    "run_referee",
    "run_tool_grounded_checks",
]
