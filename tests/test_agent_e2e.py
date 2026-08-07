"""End-to-end agent loop with a scripted model (CI stays offline)."""
from __future__ import annotations

from konigsberg_harness.agent import Agent, AgentConfig
from konigsberg_harness.ledger import Claim, TrustRoot, mint_certificate
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall
from konigsberg_harness.tools.arg_models import ChoosabilityRefuteArgs, VerifyColoringArgs
from konigsberg_harness.tools.registry import ToolRegistry


class ScriptedModel:
    def __init__(self, responses: list):
        self._responses = list(responses)
        self.histories: list[list[HistoryItem]] = []

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        self.histories.append(list(history))
        return self._responses.pop(0)


def test_e2e_choosability_refute_mints_certificate_or_enumeration():
    """Scripted model calls choosability_refute; ledger gets a tool-minted Claim."""

    def fake_refute(graph6: str, k: int = 3, palette: int | None = None) -> Claim:
        return mint_certificate(
            f"{graph6} is NOT {k}-choosable (stub)",
            checker="stub",
            tool="choosability_refute",
        )

    reg = ToolRegistry()
    reg.register(
        "choosability_refute",
        fake_refute,
        "stub refute",
        args_model=ChoosabilityRefuteArgs,
    )
    model = ScriptedModel(
        [
            [ToolCall(id="1", name="choosability_refute", args={"graph6": "Dhc", "k": 2})],
            AssistantText("C5 is not 2-choosable"),
        ]
    )
    result = Agent(reg, model, AgentConfig(max_steps=5)).run(
        "decide whether C5 is 2-choosable and record the result"
    )
    assert result.final is not None
    assert len(result.ledger.claims()) == 1
    claim = result.ledger.claims()[0]
    assert claim.provenance.trust_root is TrustRoot.CERTIFICATE
    assert "choosability_refute" in claim.provenance.tool


def test_e2e_verify_coloring_mints_proved():
    def fake_verify(graph6: str, coloring: list[int]) -> Claim:
        from konigsberg_harness.ledger import mint_lean_proof

        return mint_lean_proof(
            f"{graph6} admits proper coloring {coloring} (kernel-checked)",
            axioms=("propext", "Quot.sound"),
            tool="verify_coloring",
        )

    reg = ToolRegistry()
    reg.register(
        "verify_coloring",
        fake_verify,
        "stub verify",
        args_model=VerifyColoringArgs,
    )
    model = ScriptedModel(
        [
            [
                ToolCall(
                    id="1",
                    name="verify_coloring",
                    args={"graph6": "A_", "coloring": [0, 1]},
                )
            ],
            AssistantText("edge is 2-colored"),
        ]
    )
    result = Agent(reg, model).run("verify a 2-coloring of K2")
    assert result.ledger.claims()[0].provenance.label() == "proved"
    assert result.ledger.claims()[0].provenance.trust_root is TrustRoot.LEAN_KERNEL
