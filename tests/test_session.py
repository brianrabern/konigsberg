"""SessionStore round-trip + resume preserves ledger trust roots."""
from __future__ import annotations

from konigsberg_harness.ledger import TrustRoot, mint_enumeration, mint_lean_proof
from konigsberg_harness.models import AssistantText, ToolCall, ToolResultMsg, UserMsg
from konigsberg_harness.session import SessionStore, claim_to_dict


def test_session_round_trip(tmp_path):
    store = SessionStore(tmp_path)
    sess = store.create()
    store.log_user(sess, "check P3")
    store.log_history_item(
        sess, ToolCall(id="1", name="verify_coloring", args={"graph6": "Bg", "coloring": [0, 1, 0]})
    )
    store.log_history_item(
        sess, ToolResultMsg(id="1", content="[proved] ok")
    )
    claim = mint_lean_proof(
        "Bg admits proper coloring [0, 1, 0]",
        axioms=("propext", "Quot.sound"),
        tool="verify_coloring",
    )
    store.log_claim(sess, claim)
    store.log_history_item(sess, AssistantText("done"))

    loaded = store.load(sess.id)
    assert loaded.id == sess.id
    assert len(loaded.history) == 4
    assert isinstance(loaded.history[0], UserMsg)
    assert isinstance(loaded.history[1], ToolCall)
    assert loaded.history[1].args["graph6"] == "Bg"
    assert len(loaded.ledger.claims()) == 1
    assert loaded.ledger.claims()[0].provenance.trust_root is TrustRoot.LEAN_KERNEL
    assert loaded.ledger.claims()[0].provenance.label() == "proved"
    assert claim_to_dict(loaded.ledger.claims()[0])["statement"] == claim.statement


def test_resume_preserves_enumeration_trust_root(tmp_path):
    store = SessionStore(tmp_path)
    sess = store.create()
    c = mint_enumeration("no cx", bound="n<=3", exhaustive=True, tool="counterexample_search")
    store.log_claim(sess, c)
    loaded = store.load(sess.id)
    assert loaded.ledger.claims()[0].provenance.trust_root is TrustRoot.ENUMERATION


def test_latest_and_continue(tmp_path):
    store = SessionStore(tmp_path)
    a = store.create()
    store.log_user(a, "first")
    b = store.create()
    store.log_user(b, "second")
    assert store.latest_id() == b.id
    latest = store.latest()
    assert latest is not None
    assert latest.history[0].text == "second"


def test_compact_event_replays_history(tmp_path):
    store = SessionStore(tmp_path)
    sess = store.create()
    store.log_user(sess, "old1")
    store.log_user(sess, "old2")
    store.log_user(sess, "keep-me")
    claim = mint_enumeration("x", bound="n<=1", exhaustive=True, tool="t")
    store.log_claim(sess, claim)
    store.log_compaction(
        sess,
        summary="Summary of earlier work: did stuff",
        kept=[UserMsg("keep-me")],
    )
    loaded = store.load(sess.id)
    assert len(loaded.history) == 2
    assert "Summary" in loaded.history[0].text
    assert loaded.history[1].text == "keep-me"
    assert len(loaded.ledger.claims()) == 1  # claim survived compaction event
