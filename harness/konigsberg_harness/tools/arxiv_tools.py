"""arXiv Atom API search. Retrieval only — never mints Claims.

Hits are unverified external bibliographic pointers for the References zone.
They are not corpus status and not ledger establishment.

Respects arXiv API TOU pacing: ≤1 request / 3s, single flight, retry on 429 /
soft ``Rate exceeded.`` responses.
"""

from __future__ import annotations

import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from .errors import ToolUnavailable

_ATOM = "{http://www.w3.org/2005/Atom}"
_ARXIV = "{http://arxiv.org/schemas/atom}"
_DEFAULT_UA = "konigsberg/0.1 (research assistant; +https://github.com/)"
_API = "https://export.arxiv.org/api/query"
_MIN_INTERVAL_S = 3.0
_MAX_ATTEMPTS = 4

_lock = threading.Lock()
_last_request_at = 0.0


class ArxivUnavailable(ToolUnavailable):
    """Network / API failure talking to export.arxiv.org."""

    def __init__(self, reason: str) -> None:
        super().__init__("arxiv_search", reason)


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return " ".join(el.text.split())


def _entry_id(raw: str) -> str:
    # http://arxiv.org/abs/1602.02589v1 → 1602.02589
    s = raw.rsplit("/", 1)[-1]
    if "v" in s and s.rsplit("v", 1)[-1].isdigit():
        s = s.rsplit("v", 1)[0]
    return s


def _parse_feed(xml_bytes: bytes, *, summary_chars: int) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    out: list[dict[str, Any]] = []
    for entry in root.findall(f"{_ATOM}entry"):
        raw_id = _text(entry.find(f"{_ATOM}id"))
        arxiv_id = _entry_id(raw_id)
        title = _text(entry.find(f"{_ATOM}title"))
        summary = _text(entry.find(f"{_ATOM}summary"))
        if len(summary) > summary_chars:
            summary = summary[: summary_chars - 1].rstrip() + "…"
        authors = [
            _text(a.find(f"{_ATOM}name"))
            for a in entry.findall(f"{_ATOM}author")
            if _text(a.find(f"{_ATOM}name"))
        ]
        published = _text(entry.find(f"{_ATOM}published"))[:10]
        cats = [
            c.attrib.get("term", "")
            for c in entry.findall(f"{_ARXIV}primary_category")
            + entry.findall(f"{_ATOM}category")
            if c.attrib.get("term")
        ]
        # dedupe categories, keep order
        seen: set[str] = set()
        categories: list[str] = []
        for c in cats:
            if c not in seen:
                seen.add(c)
                categories.append(c)
        pdf = ""
        page = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else raw_id
        for link in entry.findall(f"{_ATOM}link"):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf = link.attrib.get("href", "")
                break
        out.append(
            {
                "source": "arxiv",
                "status": "arxiv",
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "summary": summary,
                "published": published,
                "url": page,
                "pdf_url": pdf or (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else ""),
                "categories": categories,
            }
        )
    return out


def _is_rate_exceeded_body(body: bytes) -> bool:
    head = body[:64].lstrip().lower()
    return head.startswith(b"rate exceeded")


def _pace() -> None:
    """Enforce arXiv TOU: no more than one request every three seconds."""
    global _last_request_at
    with _lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL_S - (now - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _fetch(url: str) -> bytes:
    """GET with pacing + retries on HTTP 429 / soft rate-limit body."""
    req = urllib.request.Request(url, headers={"User-Agent": _DEFAULT_UA})
    last_err: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        _pace()
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and attempt + 1 < _MAX_ATTEMPTS:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                try:
                    delay = float(retry_after) if retry_after else 5.0 * (attempt + 1)
                except ValueError:
                    delay = 5.0 * (attempt + 1)
                time.sleep(max(delay, _MIN_INTERVAL_S))
                continue
            if e.code == 429:
                raise ArxivUnavailable(
                    "arXiv rate-limited this IP (HTTP 429). Wait ~a minute and "
                    "retry; avoid rapid repeated arxiv_search calls."
                ) from e
            raise ArxivUnavailable(f"arxiv API request failed: {e}") from e
        except urllib.error.URLError as e:
            raise ArxivUnavailable(f"arxiv API request failed: {e}") from e

        if _is_rate_exceeded_body(body):
            last_err = RuntimeError("Rate exceeded.")
            if attempt + 1 < _MAX_ATTEMPTS:
                time.sleep(5.0 * (attempt + 1))
                continue
            raise ArxivUnavailable(
                "arXiv rate-limited this IP (soft 'Rate exceeded.'). Wait ~a "
                "minute and retry; avoid rapid repeated arxiv_search calls."
            ) from last_err
        return body

    raise ArxivUnavailable(f"arxiv API request failed: {last_err}")


def arxiv_search(
    query: str,
    *,
    max_results: int = 5,
    sort_by: str = "relevance",
    category: str | None = None,
    summary_chars: int = 400,
) -> list[dict[str, Any]]:
    """Search arXiv via the public Atom API.

    Returns hit dicts with ``source="arxiv"`` / ``status="arxiv"``. Does **not**
    mint ledger Claims — bibliographic lookup ≠ establishment. Prefer
    ``literature_search`` first for in-repo formalized/stated results.
    """
    q = query.strip()
    if not q:
        return []
    max_results = max(1, min(int(max_results), 25))
    # Restrict to math.CO by default when category omitted? User may want open
    # search — keep category optional and prepend when set.
    search_query = q
    if category:
        cat = category.strip()
        if cat and not cat.startswith("cat:"):
            search_query = f"cat:{cat} AND ({q})"
        elif cat:
            search_query = f"{cat} AND ({q})"

    sort_map = {
        "relevance": "relevance",
        "lastUpdatedDate": "lastUpdatedDate",
        "submittedDate": "submittedDate",
    }
    sortBy = sort_map.get(sort_by, "relevance")

    params = urllib.parse.urlencode(
        {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": sortBy,
            "sortOrder": "descending",
        }
    )
    url = f"{_API}?{params}"
    body = _fetch(url)
    return _parse_feed(body, summary_chars=summary_chars)
