"""The trust spine must behave. These assertions are the point of the project."""
from konigsberg_harness import ledger as L


def test_labels_map_from_trust_root():
    proved = L.mint_lean_proof("thm", axioms=("propext",), tool="lean_prove")
    modax = L.mint_lean_proof("thm", axioms=("Lean.ofReduceBool",), tool="lean_prove")
    stated = L.mint_lean_statement("thm", tool="lean_typecheck_statement")
    cert = L.mint_certificate("AT", checker="verify", tool="alon_tarsi")
    solver = L.mint_solver_result("fb", tool="fixer_breaker")
    enum = L.mint_enumeration("no cx", bound="n<=10", exhaustive=True, tool="cx")
    conj = L.mint_conjecture("maybe")

    assert proved.provenance.label() == "proved"
    assert modax.provenance.label() == "proved-mod-axioms"
    assert stated.provenance.label() == "stated"
    assert cert.provenance.label() == "certificate-checked"
    assert solver.provenance.label() == "solver-certified"
    assert enum.provenance.label() == "python-checked"
    assert conj.provenance.label() == "conjectured"


def test_solver_and_proved_have_different_trust_roots():
    # The whole reason status is not a linear rank.
    solver = L.mint_solver_result("x", tool="fb")
    proved = L.mint_lean_proof("x", axioms=(), tool="lp")
    assert solver.provenance.trust_root is L.TrustRoot.SOLVER
    assert proved.provenance.trust_root is L.TrustRoot.LEAN_KERNEL


def test_ledger_is_append_only_and_has_no_upgrade():
    led = L.Ledger()
    led.record(L.mint_conjecture("c"))
    assert not hasattr(led, "upgrade")
    assert len(led.claims()) == 1


def test_stated_carries_no_truth_evidence():
    stated = L.mint_lean_statement("thm", tool="t")
    assert stated.provenance.evidence_kind is L.EvidenceKind.WELL_FORMED_ONLY
    assert stated.provenance.well_formed is True
