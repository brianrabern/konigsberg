"""arxiv_search: Atom parse, registry wiring, References (arxiv) — no Claims."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from konigsberg_harness.agent import Agent, AssistantFinal
from konigsberg_harness.grounding import (
    GROUNDING_SYSTEM_PROMPT,
    format_arxiv_references_zone,
    format_grounded_answer,
    format_references_zone,
)
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall
from konigsberg_harness.session import Session
from konigsberg_harness.tools import arxiv_tools as ax
from konigsberg_harness.tools.arxiv_tools import ArxivUnavailable, _parse_feed, arxiv_search
from konigsberg_harness.tools.registry import build_registry

_SAMPLE_ATOM = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1602.02589v1</id>
    <published>2016-02-08T00:00:00Z</published>
    <title>Improved lower bounds on the number of edges in
      list critical and online list critical graphs</title>
    <summary>We prove new lower bounds on the number of edges
      in k-list-critical graphs.</summary>
    <author><name>Daniel W. Cranston</name></author>
    <author><name>Landon Rabern</name></author>
    <link href="http://arxiv.org/pdf/1602.02589v1" rel="related"
          type="application/pdf" title="pdf"/>
    <arxiv:primary_category term="math.CO"/>
    <category term="math.CO" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
"""


@pytest.fixture(autouse=True)
def _fast_arxiv_pacing(monkeypatch):
    """Don't sleep in unit tests; reset process-wide pacing clock."""
    monkeypatch.setattr(ax, "_last_request_at", 0.0)
    monkeypatch.setattr(ax, "_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(ax.time, "sleep", lambda *_a, **_k: None)


def test_parse_feed_extracts_hit_fields():
    hits = _parse_feed(_SAMPLE_ATOM, summary_chars=400)
    assert len(hits) == 1
    h = hits[0]
    assert h["source"] == "arxiv"
    assert h["status"] == "arxiv"
    assert h["arxiv_id"] == "1602.02589"
    assert "list critical" in h["title"].lower()
    assert h["authors"] == ["Daniel W. Cranston", "Landon Rabern"]
    assert h["published"] == "2016-02-08"
    assert h["url"] == "https://arxiv.org/abs/1602.02589"
    assert "math.CO" in h["categories"]
    assert h["summary"].startswith("We prove")


def test_arxiv_search_mocks_urlopen_and_builds_query():
    mock_resp = MagicMock()
    mock_resp.read.return_value = _SAMPLE_ATOM
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False

    with patch(
        "konigsberg_harness.tools.arxiv_tools.urllib.request.urlopen",
        return_value=mock_resp,
    ) as opener:
        hits = arxiv_search("list critical", max_results=3, category="math.CO")

    assert len(hits) == 1
    assert hits[0]["arxiv_id"] == "1602.02589"
    called_url = opener.call_args[0][0]
    if hasattr(called_url, "full_url"):
        called_url = called_url.full_url
    else:
        called_url = str(called_url)
    assert "export.arxiv.org/api/query" in called_url
    assert "cat%3Amath.CO" in called_url or "cat:math.CO" in called_url
    assert "list+critical" in called_url or "list%20critical" in called_url


def test_arxiv_search_empty_query():
    assert arxiv_search("  ") == []


def test_arxiv_search_retries_http_429_then_succeeds():
    err = ax.urllib.error.HTTPError(
        url="https://export.arxiv.org/api/query",
        code=429,
        msg="Unknown Error",
        hdrs=None,
        fp=None,
    )
    ok = MagicMock()
    ok.read.return_value = _SAMPLE_ATOM
    ok.__enter__.return_value = ok
    ok.__exit__.return_value = False

    with patch(
        "konigsberg_harness.tools.arxiv_tools.urllib.request.urlopen",
        side_effect=[err, ok],
    ) as opener:
        hits = arxiv_search("list critical", category=None)
    assert hits[0]["arxiv_id"] == "1602.02589"
    assert opener.call_count == 2


def test_arxiv_search_rate_exceeded_body_retries():
    soft = MagicMock()
    soft.read.return_value = b"Rate exceeded."
    soft.__enter__.return_value = soft
    soft.__exit__.return_value = False
    ok = MagicMock()
    ok.read.return_value = _SAMPLE_ATOM
    ok.__enter__.return_value = ok
    ok.__exit__.return_value = False

    with patch(
        "konigsberg_harness.tools.arxiv_tools.urllib.request.urlopen",
        side_effect=[soft, ok],
    ):
        hits = arxiv_search("list critical", category=None)
    assert hits[0]["arxiv_id"] == "1602.02589"


def test_arxiv_search_429_exhausted_is_unavailable():
    err = ax.urllib.error.HTTPError(
        url="https://export.arxiv.org/api/query",
        code=429,
        msg="Unknown Error",
        hdrs=None,
        fp=None,
    )
    with (
        patch(
            "konigsberg_harness.tools.arxiv_tools.urllib.request.urlopen",
            side_effect=err,
        ),
        patch.object(ax, "_MAX_ATTEMPTS", 2),
        pytest.raises(ArxivUnavailable, match="rate-limited"),
    ):
        arxiv_search("list critical", category=None)


def test_arxiv_search_registered_no_claims():
    reg = build_registry()
    assert "arxiv_search" in reg.names()
    specs = {t["name"]: t for t in reg.tool_specs()}
    assert "arxiv_search" in specs
    assert specs["arxiv_search"]["input_schema"]["properties"].keys() >= {
        "query",
        "max_results",
        "sort_by",
        "category",
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = _SAMPLE_ATOM
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    with patch(
        "konigsberg_harness.tools.arxiv_tools.urllib.request.urlopen",
        return_value=mock_resp,
    ):
        hits = reg.dispatch("arxiv_search", {"query": "list critical", "max_results": 2})
    assert hits and hits[0]["status"] == "arxiv"


def test_arxiv_references_zone_separate_from_corpus():
    ax_hit = [
        {
            "source": "arxiv",
            "status": "arxiv",
            "arxiv_id": "1602.02589",
            "title": "Improved lower bounds",
            "authors": ["Cranston", "Rabern"],
            "published": "2016-02-08",
            "url": "https://arxiv.org/abs/1602.02589",
        }
    ]
    corpus = [
        {
            "name": "RabernBook_FirstListBound",
            "lean_name": "Konigsberg.Literature.Coloring.RabernBook_FirstListBound.x",
            "status": "formalized",
            "provenance": "",
        }
    ]
    mixed = corpus + ax_hit
    assert "1602.02589" not in format_references_zone(mixed)
    assert "formalized" in format_references_zone(mixed)
    arxiv_body = format_arxiv_references_zone(mixed)
    assert "arXiv:1602.02589" in arxiv_body
    assert "Cranston" in arxiv_body
    text = format_grounded_answer(commentary="leads only", claims=(), references=mixed)
    assert "References (corpus):" in text
    assert "References (arxiv):" in text
    assert "Established (ledger):\n(nothing established)" in text
    assert text.index("References (corpus):") < text.index("References (arxiv):")
    assert text.index("References (arxiv):") < text.index("Commentary:")


def test_grounding_prompt_mentions_arxiv_search():
    assert "arxiv_search" in GROUNDING_SYSTEM_PROMPT
    assert "References (arxiv)" in GROUNDING_SYSTEM_PROMPT


class _Scripted:
    def __init__(self, responses):
        self._responses = list(responses)

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        return self._responses.pop(0)


def test_agent_arxiv_search_fills_references_ledger_empty():
    reg = build_registry()
    mock_resp = MagicMock()
    mock_resp.read.return_value = _SAMPLE_ATOM
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False

    model = _Scripted(
        [
            [ToolCall(id="1", name="arxiv_search", args={"query": "list critical"})],
            AssistantText("Bibliographic leads only; nothing established."),
        ]
    )
    with patch(
        "konigsberg_harness.tools.arxiv_tools.urllib.request.urlopen",
        return_value=mock_resp,
    ):
        agent = Agent(reg, model)
        session = Session.create()
        from konigsberg_harness.models import UserMsg

        session.history.append(UserMsg("any arxiv on list-critical?"))
        events = list(agent.step(session))
    final = next(e for e in events if isinstance(e, AssistantFinal))
    assert "References (arxiv):" in final.text
    assert "1602.02589" in final.text
    assert len(session.ledger.claims()) == 0
    assert len(final.claims) == 0
    assert final.references
    assert any(r.get("source") == "arxiv" for r in final.references)
