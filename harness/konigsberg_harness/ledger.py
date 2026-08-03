"""Epistemic ledger — the trust spine.

The single most important subsystem. Everything else is replaceable; this is not.

Two design commitments, both load-bearing:

1. Status is a STRUCTURED RECORD, not a linear rank. `proved` (Lean kernel) and
   `solver-certified` (empirical port) do not differ in *degree* of trust; they
   differ in *trust root* — the thing the buck stops at. Collapsing them onto one
   ordinal hides exactly the distinction this project exists to make explicit.
   So a claim carries a `Provenance`: {trust_root, evidence_kind, well_formed,
   bound, axioms, tool}. Human-facing labels ("proved", "python-checked") are a
   *view* derived from that record, never its source of truth.

2. The agent is STRUCTURALLY INCAPABLE of upgrading status. There is no
   `upgrade()`. A `Claim` is minted only from a tool result, via the
   `mint_*` constructors below, which stamp the trust root themselves. The model
   can hand us a string; it cannot hand us a `Provenance`.

See also the merge-time twin of this guarantee: ci/check_axioms.py,
ci/check_no_sorry.py, ci/check_status.py. Same guarantee, two moments.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field, replace
from enum import Enum


# Axioms Lean's `#print axioms` may report without escalating trust. Everything
# else requires explicit, written per-case justification. `native_decide` is
# deliberately absent: it trusts the compiler, not just the kernel.
AXIOM_WHITELIST: frozenset[str] = frozenset(
    {"propext", "Classical.choice", "Quot.sound"}
)


class TrustRoot(Enum):
    """Where the buck stops for a claim. This is the axis that actually matters."""

    LEAN_KERNEL = "lean_kernel"      # Lean typechecker + whitelisted axioms
    CERTIFICATE = "certificate"      # solver emitted a finite object we RE-CHECKED
    SOLVER = "solver"                # solver asserted; port validated vs oracle, not re-checked
    ENUMERATION = "enumeration"      # exhaustive / sampled empirical check to a bound
    MODEL = "model"                  # raw LLM output


class EvidenceKind(Enum):
    """What *kind* of thing supports the claim — orthogonal to trust root."""

    PROOF = "proof"
    CERTIFICATE = "certificate"
    EXHAUSTIVE = "exhaustive"
    SAMPLED = "sampled"
    WELL_FORMED_ONLY = "well_formed_only"  # typechecks as a Prop; says NOTHING about truth
    NONE = "none"


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


@dataclass(frozen=True)
class Provenance:
    """Immutable record of how a claim was established. Frozen on purpose."""

    trust_root: TrustRoot
    evidence_kind: EvidenceKind
    well_formed: bool                       # did it at least typecheck as a proposition?
    bound: str | None = None                # e.g. "n<=10" for enumeration/sampled
    axioms: tuple[str, ...] = ()            # from #print axioms, when LEAN_KERNEL
    tool: str = ""                          # which tool minted this
    at: str = field(default_factory=_utcnow)

    @property
    def nonstandard_axioms(self) -> tuple[str, ...]:
        return tuple(a for a in self.axioms if a not in AXIOM_WHITELIST)

    def label(self) -> str:
        """Human-facing tag. A VIEW over the record, not the record itself."""
        r, k = self.trust_root, self.evidence_kind
        if r is TrustRoot.LEAN_KERNEL and k is EvidenceKind.PROOF:
            return "proved" if not self.nonstandard_axioms else "proved-mod-axioms"
        if r is TrustRoot.LEAN_KERNEL and k is EvidenceKind.WELL_FORMED_ONLY:
            return "stated"
        if r is TrustRoot.CERTIFICATE:
            return "certificate-checked"
        if r is TrustRoot.SOLVER:
            return "solver-certified"
        if r is TrustRoot.ENUMERATION:
            return "python-checked"
        if r is TrustRoot.MODEL:
            return "conjectured"
        return "unknown"


@dataclass(frozen=True)
class Claim:
    statement: str
    provenance: Provenance

    def render(self) -> str:
        p = self.provenance
        tag = p.label()
        extra = f" [{p.bound}]" if p.bound else ""
        if p.nonstandard_axioms:
            extra += f" axioms={{{', '.join(p.nonstandard_axioms)}}}"
        return f"[{tag}]{extra} {self.statement}"


# --- Minting constructors -------------------------------------------------
# The ONLY way a Claim comes into existence. Each is called from a tool result,
# never from model output. The trust root is stamped here, by code, not chosen
# by a caller passing a string. This is what "structurally incapable of
# upgrading status" means in practice.


def mint_lean_proof(statement: str, axioms: tuple[str, ...], *, tool: str) -> Claim:
    return Claim(
        statement,
        Provenance(
            trust_root=TrustRoot.LEAN_KERNEL,
            evidence_kind=EvidenceKind.PROOF,
            well_formed=True,
            axioms=axioms,
            tool=tool,
        ),
    )


def mint_lean_statement(statement: str, *, tool: str) -> Claim:
    """A typechecking statement whose proof is `sorry`. Well-formed only."""
    return Claim(
        statement,
        Provenance(
            trust_root=TrustRoot.LEAN_KERNEL,
            evidence_kind=EvidenceKind.WELL_FORMED_ONLY,
            well_formed=True,
            tool=tool,
        ),
    )


def mint_certificate(statement: str, *, checker: str, tool: str) -> Claim:
    """Solver emitted a finite certificate that WE independently re-checked.

    `checker` names the independent verifier (e.g. an Alon-Tarsi orientation
    re-checker, or a fixer-breaker strategy validator). Distinct from
    mint_solver_result, which trusts the solver's assertion.
    """
    return Claim(
        statement,
        Provenance(
            trust_root=TrustRoot.CERTIFICATE,
            evidence_kind=EvidenceKind.CERTIFICATE,
            well_formed=True,
            tool=f"{tool}->{checker}",
        ),
    )


def mint_solver_result(statement: str, *, tool: str) -> Claim:
    """Solver ASSERTED this; port is oracle-validated but the result is not
    independently re-checked. Strictly weaker than mint_certificate."""
    return Claim(
        statement,
        Provenance(
            trust_root=TrustRoot.SOLVER,
            evidence_kind=EvidenceKind.CERTIFICATE,
            well_formed=True,
            tool=tool,
        ),
    )


def mint_enumeration(
    statement: str, *, bound: str, exhaustive: bool, tool: str
) -> Claim:
    return Claim(
        statement,
        Provenance(
            trust_root=TrustRoot.ENUMERATION,
            evidence_kind=EvidenceKind.EXHAUSTIVE if exhaustive else EvidenceKind.SAMPLED,
            well_formed=True,
            bound=bound,
            tool=tool,
        ),
    )


def mint_conjecture(statement: str, *, tool: str = "model") -> Claim:
    return Claim(
        statement,
        Provenance(
            trust_root=TrustRoot.MODEL,
            evidence_kind=EvidenceKind.NONE,
            well_formed=False,
            tool=tool,
        ),
    )


class Ledger:
    """Append-only record of every claim surfaced during a session.

    Append-only is the point: there is no mutate and no upgrade. If a `stated`
    claim later gets proved, that is a NEW claim with a NEW provenance; the old
    one stays in the record. History of how belief was warranted is preserved.
    """

    def __init__(self) -> None:
        self._claims: list[Claim] = []

    def record(self, claim: Claim) -> Claim:
        if not isinstance(claim, Claim):  # defensive: only minted Claims enter
            raise TypeError("Ledger only accepts Claim objects minted by ledger.mint_*")
        self._claims.append(claim)
        return claim

    def claims(self) -> tuple[Claim, ...]:
        return tuple(self._claims)

    def by_trust_root(self, root: TrustRoot) -> tuple[Claim, ...]:
        return tuple(c for c in self._claims if c.provenance.trust_root is root)

    def render(self) -> str:
        return "\n".join(c.render() for c in self._claims)


__all__ = [
    "AXIOM_WHITELIST",
    "TrustRoot",
    "EvidenceKind",
    "Provenance",
    "Claim",
    "Ledger",
    "mint_lean_proof",
    "mint_lean_statement",
    "mint_certificate",
    "mint_solver_result",
    "mint_enumeration",
    "mint_conjecture",
]
