#!/usr/bin/env python3
"""hunt_watch — live, read-only progress dashboard for a running BK campaign.

Tails a session JSONL under ``~/.konigsberg/sessions/`` and renders the campaign
staircase as a color terminal panel: distinct forbidden cores, durable lemmas
(highlighted when freshly proved), the latest discharging attempt, a claims
breakdown, an activity pulse with health flags, a color-coded recent-event feed,
and a settlement watch. Never writes — safe to run in a second pane while
``--forever`` runs.

Usage
-----
  make watch                                          # latest session, 3s refresh
  uv run python scripts/hunt_watch.py                 # same
  uv run python scripts/hunt_watch.py --once          # one snapshot, then exit
  uv run python scripts/hunt_watch.py --session ID --interval 10
  uv run python scripts/hunt_watch.py --no-color      # plain (or set NO_COLOR=1)

Pairs with:  uv run konig --forever   (other pane)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CORE_RE = re.compile(r"core=([^,\s]+)")
_DEFAULT_DIR = Path.home() / ".konigsberg" / "sessions"
_W = 72  # panel width
# Illegal discharging args + session Ctrl-C + the fixed Zykov-join bug are
# history, not hunt health. Don't paint the panel red for them.
_IGNORED_ERR = (
    "μ must specify degrees",
    "non-conserving rule",
    "Caught keyboard interrupt",
    "module 'networkx' has no attribute 'join'",
    "unknown graph kind 'join'",
    "kind='join' is Zykov",
    "LEAN COMPILE MISS",
    "proof failed:",
    "durable proof failed",
    "does not elaborate",
    "validation errors for DischargingArgs",
    "#print axioms",
    "invalid 'import' command",
    "exceeds live cap",
    "timed out after",
    "TOOL BUDGET EXCEEDED",
)


# ── colour ────────────────────────────────────────────────────────────────
class C:
    enabled = True

    def __getattr__(self, name: str) -> str:  # lazy codes; disabled → ""
        codes = {
            "reset": "0", "bold": "1", "dim": "2", "ital": "3", "blink": "5",
            "red": "31", "green": "32", "yellow": "33", "blue": "34",
            "magenta": "35", "cyan": "36", "white": "37", "grey": "90",
            "bgreen": "92", "byellow": "93", "bblue": "94", "bmagenta": "95",
            "bcyan": "96",
        }
        if not C.enabled or name not in codes:
            return ""
        return f"\033[{codes[name]}m"


c = C()


def paint(s: str, *styles: str) -> str:
    if not C.enabled or not styles:
        return s
    return "".join(styles) + s + c.reset


# ── io ──────────────────────────────────────────────────────────────────────
def _sessions_dir(arg: str | None) -> Path:
    return Path(arg).expanduser() if arg else _DEFAULT_DIR


def _latest_session(d: Path) -> str | None:
    paths = list(d.glob("*.jsonl"))
    return max(paths, key=lambda p: p.stat().st_mtime).stem if paths else None


def _read_events(path: Path) -> list[dict]:
    out: list[dict] = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return out


def _ts(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


def _age(ts: datetime | None) -> tuple[str, int]:
    if ts is None:
        return "?", -1
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    secs = max(int((datetime.now(timezone.utc) - ts).total_seconds()), 0)
    if secs < 90:
        return f"{secs}s", secs
    if secs < 5400:
        return f"{secs // 60}m", secs
    return f"{secs // 3600}h{(secs % 3600) // 60}m", secs


def _hhmmss(ts: datetime | None) -> str:
    return ts.astimezone().strftime("%H:%M:%S") if ts else "--:--:--"


def _is_health_error(ev: dict) -> bool:
    """True for unexpected tool failures that should flag the dashboard."""
    if not ev.get("is_error"):
        return False
    body = str(ev.get("content") or "")
    return not any(needle in body for needle in _IGNORED_ERR)


# ── parse ─────────────────────────────────────────────────────────────────
def _claim_fields(ev: dict) -> tuple[str, str, bool]:
    stmt = str(ev.get("statement") or "")
    prov = ev.get("provenance") if isinstance(ev.get("provenance"), dict) else ev
    return stmt, str(prov.get("tool") or ""), bool(prov.get("durable"))


def _classify(stmt: str, tool: str) -> str:
    s = stmt.upper()
    if "FORBIDDEN CONFIGURATION" in s:
        return "forbidden-config"
    # Real HITs are minted by discharging_unavoidable as
    # "UNAVOIDABLE (BK D=… discharging): cores=…". Do not match the
    # substring UNAVOIDABLE — Lean names like
    # reducible_and_unavoidable_imp_no_counterexample would false-close.
    if tool == "discharging_unavoidable" or s.startswith("UNAVOIDABLE (BK"):
        return "discharging"
    if "VIOLATES BK" in s:
        return "BK-violation(!)"
    if tool == "lean_prove":
        return "lean-proof"
    if tool in ("reed_sweep", "counterexample_search", "bk_search"):
        return "census/search"
    if tool == "reducible_configuration":
        return "reducible-hit"
    return tool or "other"


def summarize(events: list[dict]) -> dict:
    claims = [e for e in events if e.get("type") == "claim"]
    lemmas = [e for e in events if e.get("type") == "lemma"]
    tcalls = [e for e in events if e.get("type") == "tool_call"]
    tres = [e for e in events if e.get("type") == "tool_result"]
    asst = [e for e in events if e.get("type") == "assistant"]
    users = [e for e in events if e.get("type") == "user"]
    meta = next((e for e in events if e.get("type") == "session_meta"), {})

    cores: list[str] = []
    kinds: Counter = Counter()
    settlement = last_discharge = None
    for e in claims:
        stmt, tool, _d = _claim_fields(e)
        k = _classify(stmt, tool)
        kinds[k] += 1
        if k == "forbidden-config":
            m = CORE_RE.search(stmt)
            if m and m.group(1) not in cores:
                cores.append(m.group(1))
        if k == "discharging":
            last_discharge = stmt[:110]
        if "VIOLATES BK" in stmt.upper():
            settlement = "BK VIOLATION claim — verify: " + stmt[:80]
    for e in asst:
        t = str(e.get("text") or "")
        if "PROVED" in t and "Borodin" in t:
            settlement = t[:150]

    # discharging: attempts vs closures (discharging_unavoidable HIT claims)
    call_name = {e.get("id"): e.get("name") for e in tcalls}
    disc_res = [e for e in tres if call_name.get(e.get("id")) == "discharging_unavoidable"]
    disc_attempts = sum(1 for e in tcalls if e.get("name") == "discharging_unavoidable")
    disc_closed = kinds.get("discharging", 0)
    last_survivor = (str(disc_res[-1].get("content") or "")[:96] if disc_res else None)

    durable = [(l.get("lean_name", "?"), True) for l in lemmas if l.get("durable")]
    sess_lemmas = [(l.get("lean_name", "?"), False) for l in lemmas if not l.get("durable")]
    errors = [e for e in tres if _is_health_error(e)]
    n_err_recent = sum(1 for e in errors if _age(_ts(e.get("at")))[1] < 120)
    redisc = sum(1 for e in events if "REDISCOVERY" in str(e.get("text") or "").upper())

    ts_all = [t for t in (_ts(e.get("at")) for e in events) if t]
    started = _ts(meta.get("created_at")) or (ts_all[0] if ts_all else None)
    last = ts_all[-1] if ts_all else None

    # recent feed (last 12 events, oldest→newest)
    recent = [(e.get("type"), _ts(e.get("at")), e) for e in events[-12:]]

    return {
        "session": meta.get("id", "?"), "started": started, "last": last,
        "n_claims": len(claims), "kinds": kinds, "cores": cores,
        "durable": durable, "session_lemmas": sess_lemmas, "n_lemmas": len(lemmas),
        "tool_hist": Counter(str(e.get("name") or "?") for e in tcalls),
        "n_tcalls": len(tcalls), "n_asst": len(asst), "n_user": len(users),
        "n_err": len(errors),
        "n_err_recent": n_err_recent,
        "last_err": (str(errors[-1].get("content") or "")[:70] if errors else ""),
        "redisc": redisc, "last_discharge": last_discharge,
        "disc_attempts": disc_attempts, "disc_closed": disc_closed,
        "last_survivor": last_survivor,
        "settlement": settlement, "recent": recent,
    }


# ── render ────────────────────────────────────────────────────────────────
def _rule(ch: str = "─") -> str:
    return paint(ch * _W, c.grey)


def _feed_line(kind, ts, ev) -> str:
    t = paint(_hhmmss(ts), c.grey)
    if kind == "claim":
        stmt, tool, dur = _claim_fields(ev)
        k = _classify(stmt, tool)
        badge = paint(" durable", c.bgreen) if dur else ""
        glyph = paint("✓", c.green)
        body = paint(f"{k}", c.green) + badge + paint(f"  {stmt[:44]}", c.white)
        return f"{t} {glyph} {body}"
    if kind == "lemma":
        name = str(ev.get("lean_name", "?")).split(".")[-1]
        dur = ev.get("durable")
        glyph = paint("★", c.bgreen if dur else c.yellow)
        tag = paint("PROVED" if dur else "locked", c.bgreen if dur else c.yellow)
        return f"{t} {glyph} {tag} {paint(name, c.bold)}"
    if kind == "tool_call":
        return f"{t} {paint('→', c.cyan)} {paint(str(ev.get('name','?')), c.cyan)}"
    if kind == "tool_result":
        body = str(ev.get("content") or "")[:40]
        if ev.get("is_error") and _is_health_error(ev):
            return f"{t} {paint('✗ error', c.red)} {paint(body, c.dim)}"
        if ev.get("is_error"):
            return f"{t} {paint('⟵ miss', c.dim)} {paint(body, c.dim)}"
        return f"{t} {paint('⟵ ok', c.dim)}"
    if kind == "assistant":
        return f"{t} {paint('· model', c.dim)} {paint(str(ev.get('text') or '')[:44], c.dim)}"
    if kind == "user":
        txt = str(ev.get("text") or "")
        tag = "continue" if ("CAMPAIGN" in txt or "STAIRCASE" in txt) else "prompt"
        return f"{t} {paint('» ' + tag, c.blue)}"
    if kind == "compaction":
        return f"{t} {paint('⋯ context compacted', c.dim)}"
    return f"{t} {paint(str(kind), c.dim)}"


def render(s: dict, flashes: list[str]) -> str:
    age_s, secs = _age(s["last"])
    if s.get("n_err_recent"):
        dot, st = paint("●", c.red), paint("errors", c.red)
    elif secs < 0 or secs > 300:
        dot, st = paint("●", c.yellow), paint("stale / maybe stuck", c.yellow)
    else:
        dot, st = paint("●", c.bgreen), paint("active", c.bgreen)

    L: list[str] = []
    L.append(_rule("═"))
    L.append(f" {dot} {paint('KÖNIGSBERG · BK HUNT', c.bold, c.bcyan)}"
             f"   {paint('session', c.grey)} {s['session']}   {st}")
    up, _ = _age(s["started"])
    L.append(f"   {paint('uptime', c.grey)} {up}   "
             f"{paint('last event', c.grey)} {age_s} ago")
    L.append(_rule("═"))

    for f in flashes:  # freshly-happened highlights
        L.append(" " + f)
    if flashes:
        L.append(_rule())

    # STAIRCASE — the real metric
    L.append(paint(" ▏STAIRCASE", c.bold))
    cores = s["cores"]
    core_n = paint(f"{len(cores)}", c.bgreen if cores else c.grey, c.bold)
    L.append(f"   forbidden cores (distinct)   {core_n}")
    if cores:
        shown = ", ".join(paint(x, c.green) for x in cores[:12])
        more = paint(f"  +{len(cores)-12}", c.grey) if len(cores) > 12 else ""
        L.append(f"     {shown}{more}")
    dl = s["durable"]
    dl_n = paint(f"{len(dl)}", c.bgreen if dl else c.grey, c.bold)
    L.append(f"   durable lemmas (kernel)      {dl_n}")
    for name, _ in dl[:8]:
        L.append(f"     {paint('★', c.bgreen)} {paint(name.split('.')[-1], c.white)}")
    att, closed = s["disc_attempts"], s["disc_closed"]
    if att == 0:
        L.append(f"   discharging   {paint('(no attempt yet)', c.grey)}")
    elif closed > 0:
        L.append("   discharging   "
                 + paint(f"✔ {closed} CLOSED / {att} attempts", c.bgreen, c.bold))
        if s["last_discharge"]:
            L.append("     " + paint(s["last_discharge"], c.bgreen))
    else:
        L.append("   discharging   "
                 + paint(f"{att} attempts · 0 closed", c.yellow)
                 + paint("  (attacking the hard half)", c.dim))
        if s["last_survivor"]:
            L.append("     " + paint("last survivor: " + s["last_survivor"], c.dim))
    L.append("")

    # CLAIMS — separate real results from graph-construction byproducts
    palette = {"forbidden-config": c.green, "discharging": c.bgreen,
               "lean-proof": c.bgreen, "reducible-hit": c.cyan,
               "census/search": c.blue, "BK-violation(!)": c.bmagenta}
    result_kinds = set(palette)
    results = [(k, n) for k, n in s["kinds"].most_common() if k in result_kinds]
    infra = [(k, n) for k, n in s["kinds"].most_common() if k not in result_kinds]
    n_res = sum(n for _, n in results)
    L.append(paint(f" ▏RESULTS  {n_res}", c.bold))
    if results:
        for k, n in results:
            bar = paint("▮" * min(n, 24), palette.get(k, c.grey))
            L.append(f"   {n:>4} {paint(k.ljust(16), palette.get(k, c.white))} {bar}")
    else:
        L.append(f"   {paint('none yet — warming up on graph construction', c.grey)}")
    if infra:
        L.append("   " + paint("infra: " + ", ".join(f"{n}×{k}" for k, n in infra),
                                c.dim))
    L.append("")

    # PULSE — health is about chatter vs tools; zero chat turns is IDEAL
    L.append(paint(" ▏PULSE", c.bold))
    tcalls, chat = s["n_tcalls"], s["n_asst"]
    healthy = tcalls > 0 and chat <= tcalls
    hc = c.bgreen if healthy else c.yellow
    label = "tool-driving" if healthy else ("idle" if tcalls == 0 else "⚠ talky")
    L.append(f"   tool calls {paint(str(tcalls), c.cyan)}   "
             f"chat turns {paint(str(chat), hc)}   "
             f"continues {max(s['n_user']-1, 0)}   {paint(label, hc)}")
    top = "  ".join(f"{paint(str(n),c.cyan)}×{name}"
                    for name, n in s["tool_hist"].most_common(6))
    L.append(f"   {top or paint('(no tool calls yet)', c.grey)}")
    if s["n_err"]:
        L.append(f"   {paint('⚠ tool errors ' + str(s['n_err']), c.red)}  "
                 f"{paint(s['last_err'], c.dim)}")
    if s["redisc"]:
        L.append(f"   {paint('↻ rediscovery ' + str(s['redisc']), c.yellow)} "
                 f"{paint('(staircase steering off dupes)', c.dim)}")
    L.append("")

    # SETTLEMENT
    if s["settlement"]:
        L.append(paint(" ‼ SETTLEMENT SIGNAL — verify in ledger (kernel is the warrant)",
                       c.bmagenta, c.bold, c.blink))
        L.append("   " + paint(s["settlement"], c.bmagenta))
    else:
        L.append(f" {paint('settlement', c.grey)} "
                 f"{paint('none (expected — judge by the staircase)', c.dim)}")
    L.append(_rule())

    # RECENT FEED
    L.append(paint(" ▏RECENT", c.bold))
    for kind, ts, ev in s["recent"]:
        L.append("   " + _feed_line(kind, ts, ev))
    L.append(_rule("═"))
    return "\n".join(L)


def _flashes(prev: dict | None, cur: dict) -> list[str]:
    if not prev:
        return []
    out: list[str] = []
    dc = len(cur["cores"]) - len(prev["cores"])
    if dc > 0:
        out.append(paint(f"＋{dc} forbidden core", c.green, c.bold)
                   + paint(f"   → {', '.join(cur['cores'][-dc:])}", c.green))
    prev_names = {n for n, _ in prev["durable"]}
    new_proved = [n for n, _ in cur["durable"] if n not in prev_names]
    for n in new_proved:
        out.append(paint(f"★ NEW LEMMA PROVED  {n.split('.')[-1]}", c.bgreen, c.bold))
    if cur["disc_closed"] > prev.get("disc_closed", 0):
        out.append(paint("✔ DISCHARGING CLOSED a set — big deal, verify it", c.bgreen, c.bold))
    if cur["settlement"] and cur["settlement"] != prev.get("settlement"):
        out.append(paint("‼ SETTLEMENT SIGNAL just appeared", c.bmagenta, c.bold))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Live BK hunt progress dashboard.")
    p.add_argument("--session")
    p.add_argument("--sessions-dir")
    p.add_argument("--interval", type=float, default=3.0)
    p.add_argument("--once", action="store_true")
    p.add_argument("--no-color", action="store_true")
    args = p.parse_args(argv)

    C.enabled = (not args.no_color) and (os.environ.get("NO_COLOR") is None) \
        and sys.stdout.isatty()

    d = _sessions_dir(args.sessions_dir)
    sid = args.session or _latest_session(d)
    if sid is None:
        print(f"no sessions found under {d} — start `uv run konig --forever` first")
        return 1
    path = d / f"{sid}.jsonl"

    prev: dict | None = None
    try:
        while True:
            cur = summarize(_read_events(path))
            flashes = _flashes(prev, cur)
            out = render(cur, flashes)
            if args.once:
                print(out)
                return 0
            sys.stdout.write("\033[2J\033[H" + out + "\n")
            sys.stdout.flush()
            prev = cur
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
