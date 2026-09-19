"""Live-hunt Π₂ caps: n-cap and wall-clock, independent of pysat SAT search."""
from __future__ import annotations

import time

import pytest
from konigsberg_harness.tools.empirical_tools import (
    _guard_choosability_n,
    choosability_deadline,
)
from konigsberg_harness.tools.errors import ToolBudgetExceeded


def test_guard_refuses_n_over_default_cap():
    with pytest.raises(ToolBudgetExceeded, match="live cap"):
        _guard_choosability_n("choosability_refute", 9)


def test_guard_allows_n_at_cap():
    _guard_choosability_n("reducible_configuration", 6)


def test_deadline_times_out(monkeypatch):
    monkeypatch.setenv("KONIGSBERG_CHOOSABILITY_TIMEOUT", "0.15")
    with pytest.raises(ToolBudgetExceeded, match="timed out"), choosability_deadline(
        "choosability_refute"
    ):
        time.sleep(2)


def test_deadline_zero_disables(monkeypatch):
    monkeypatch.setenv("KONIGSBERG_CHOOSABILITY_TIMEOUT", "0")
    with choosability_deadline("choosability_refute"):
        pass
