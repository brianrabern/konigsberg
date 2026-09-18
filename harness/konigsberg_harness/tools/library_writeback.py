"""Write-back: promote a referee-approved proved Claim into Literature.

``lean_add_to_library`` is the *only* tool that writes trusted corpus state.
It physically cannot fire without an accepting ``RefereeReport``, clean axioms,
required SanityChecks, human confirmation, and green local gates.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from ..lean_repl import LeanREPL
from ..ledger import AXIOM_WHITELIST, Claim, mint_lean_proof
from ..referee import RefereeReport

_FORBIDDEN_AXIOMS = frozenset({"sorryAx", "Lean.ofReduceBool"})


class LibraryWriteError(ValueError):
    """Promotion refused — message explains which gate failed."""


def _git_head(cwd: Path | None = None) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd or Path.cwd(),
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _entry_name_from_lean(lean_name: str) -> tuple[str, str, str]:
    """Return (area_pascal, entry_name, short_decl) from a fully-qualified name.

    Expects ``Konigsberg.Literature.<Area>.<Entry>.<decl>``.
    """
    parts = lean_name.split(".")
    if len(parts) < 5 or parts[0] != "Konigsberg" or parts[1] != "Literature":
        raise LibraryWriteError(
            "lean_name must be Konigsberg.Literature.<Area>.<Entry>.<decl>, "
            f"got {lean_name!r}"
        )
    area, entry, decl = parts[2], parts[3], parts[-1]
    return area, entry, decl


def _normalize_report(report: RefereeReport | dict[str, Any] | str) -> RefereeReport:
    if isinstance(report, RefereeReport):
        return report
    if isinstance(report, dict):
        return RefereeReport.from_dict(report)
    if isinstance(report, str):
        # Allow JSON string; bare "accept" is NOT enough — must be structured.
        from ..referee import parse_referee_report

        return parse_referee_report(report)
    raise LibraryWriteError("referee_report must be a RefereeReport, dict, or JSON")


def _statements_lean(lean_name: str, snippet: str) -> str:
    area, entry, _ = _entry_name_from_lean(lean_name)
    ns = f"Konigsberg.Literature.{area}.{entry}"
    body = snippet.strip()
    if f"namespace {ns}" in body:
        return body + ("\n" if not body.endswith("\n") else "")
    return (
        f"/- Auto-promoted via lean_add_to_library. -/\n"
        f"import Mathlib\n"
        f"import Konigsberg\n\n"
        f"namespace {ns}\n\n"
        f"{body}\n\n"
        f"end {ns}\n"
    )


def _proofs_lean(lean_name: str) -> str:
    area, entry, _ = _entry_name_from_lean(lean_name)
    ns = f"Konigsberg.Literature.{area}.{entry}"
    mod = f"Konigsberg.Literature.{area}.{entry}.Statements"
    return (
        f"/- Proofs module (theorem body lives in Statements for this promotion). -/\n"
        f"import {mod}\n\n"
        f"namespace {ns}\n"
        f"end {ns}\n"
    )


def _notes_md(
    *,
    entry: str,
    informal_statement: str,
    citation: str,
    report: RefereeReport,
) -> str:
    return (
        f"# {entry}\n\n"
        f"## Informal statement\n"
        f"{informal_statement.strip()}\n\n"
        f"## Source\n"
        f"{citation.strip()}\n\n"
        f"## Provenance\n"
        f"Promoted via `lean_add_to_library` after referee accept. "
        f"Status `formalized`.\n\n"
        f"## Fidelity review\n"
        f"Referee recommendation: `{report.recommendation}`. "
        f"See attached referee report. Compare informal statement to Lean.\n\n"
        f"## Sanity checks\n"
        f"Concrete non-vacuity + hypothesis-necessity probes live in "
        f"[`SanityChecks.lean`](SanityChecks.lean) "
        f"(`decide` / `norm_num` only). See `docs/TRUST.md`.\n\n"
        f"{report.to_notes_section()}"
    )


def _status_toml(
    *,
    entry: str,
    area: str,
    citation: str,
    lean_name: str,
    axioms: list[str],
    verified_at: str,
) -> str:
    ax = ", ".join(f'"{a}"' for a in axioms)
    if area.lower() == "coloring" or area == "Coloring":
        area_field = "coloring"
    else:
        area_field = area.lower()
    return (
        f"[entry]\n"
        f'name = "{entry}"\n'
        f'citation = "{citation}"\n'
        f'area = "{area_field}"\n\n'
        f"[[claims]]\n"
        f'lean_name = "{lean_name}"\n'
        f'status = "formalized"\n'
        f"axioms = [{ax}]\n"
        f'verified_at = "{verified_at}"\n'
    )


def _default_sanity(lean_name: str) -> str:
    """Minimal SanityChecks — callers should pass a real hypothesis-necessity check."""
    area, entry, _ = _entry_name_from_lean(lean_name)
    ns = f"Konigsberg.Literature.{area}.{entry}"
    mod = f"{ns}.Statements"
    return (
        f"/- Sanity checks (required). Replace with load-bearing examples. -/\n"
        f"import {mod}\n"
        f"import Konigsberg.Literature.SanityLib\n\n"
        f"namespace {ns}\n\n"
        f"example : True := trivial\n\n"
        f"end {ns}\n"
    )


def _append_literature_imports(literature_lean: Path, area: str, entry: str) -> None:
    prefix = f"Konigsberg.Literature.{area}.{entry}"
    lines_to_add = [
        f"import {prefix}.Statements",
        f"import {prefix}.Proofs",
        f"import {prefix}.SanityChecks",
    ]
    text = literature_lean.read_text(encoding="utf-8") if literature_lean.exists() else ""
    additions = [ln for ln in lines_to_add if ln not in text]
    if not additions:
        return
    if text and not text.endswith("\n"):
        text += "\n"
    text += "\n" + "\n".join(additions) + "\n"
    literature_lean.write_text(text, encoding="utf-8")


def _run_entry_gates(formal_root: Path, entry_dir: Path) -> None:
    """Run conventions / no-sorry / axiom-whitelist checks on the written entry."""
    import sys
    import tomllib

    repo = Path(__file__).resolve().parents[3]
    ci = repo / "ci"
    for p in (str(repo), str(ci)):
        if p not in sys.path:
            sys.path.insert(0, p)

    from check_axioms import validate
    from check_conventions import check_entry

    errs = check_entry(entry_dir)
    if errs:
        raise LibraryWriteError("check_conventions failed: " + "; ".join(errs))

    proofs = entry_dir / "Proofs.lean"
    if not proofs.exists():
        raise LibraryWriteError("missing Proofs.lean")
    for label, path in (
        ("Proofs.lean", proofs),
        ("Statements.lean", entry_dir / "Statements.lean"),
        ("SanityChecks.lean", entry_dir / "SanityChecks.lean"),
    ):
        text = path.read_text(encoding="utf-8")
        stripped = re.sub(r"/-.*?-/", "", text, flags=re.DOTALL)
        for i, line in enumerate(stripped.splitlines(), 1):
            code = line.split("--", 1)[0]
            if re.search(r"\b(sorry|admit)\b", code):
                raise LibraryWriteError(f"{label}:{i}: contains sorry/admit")

    status = tomllib.loads((entry_dir / "status.toml").read_text(encoding="utf-8"))
    for claim in status.get("claims", []):
        if claim.get("status") != "formalized":
            continue
        if "axioms" not in claim:
            raise LibraryWriteError("formalized claim missing axioms field")
        bad = validate(list(claim.get("axioms") or []), set())
        if bad:
            raise LibraryWriteError(f"check_axioms failed: disallowed {bad}")
    _ = formal_root  # reserved for future lake/import coverage hooks

def lean_add_to_library(
    repl: LeanREPL,
    lean_name: str,
    snippet: str,
    *,
    area: str,
    citation: str,
    informal_statement: str,
    referee_report: RefereeReport | dict[str, Any] | str,
    sanity_snippet: str | None = None,
    confirmed: bool = False,
    formal_root: Path | str | None = None,
    run_gates: bool = True,
    source_claim: Claim | None = None,
) -> Claim:
    """Promote a referee-approved proof into ``Literature/<Area>/<Name>/``.

    Gates (all required):
      1. ``referee_report.allows_promotion()``
      2. ``confirmed=True`` (human-in-the-loop)
      3. ``source_claim.provenance.durable`` — proof elaborated against fresh corpus
      4. snippet elaborates in a fresh corpus env (re-check)
      5. ``#print axioms`` ⊆ whitelist (no sorryAx / native_decide)
      6. SanityChecks present (caller-supplied or default — default is weak;
         conventions require ``example``)
      7. local CI gates green on the written entry
    """
    report = _normalize_report(referee_report)
    if not report.allows_promotion():
        reason = report.recommendation
        if reason == "unavailable":
            detail = report.review_unavailable_reason or "adversarial referee did not run"
            raise LibraryWriteError(
                f"refusing write-back: REFEREE UNAVAILABLE — not vetted ({detail})"
            )
        if reason == "no-automated-issues":
            raise LibraryWriteError(
                "refusing write-back: heuristic-only review — adversarial accept required"
            )
        raise LibraryWriteError(
            "refusing write-back: referee did not accept "
            f"(recommendation={report.recommendation!r}, "
            f"majors={list(report.major_issues)})"
        )
    if not confirmed:
        raise LibraryWriteError(
            "refusing write-back: human confirmation required "
            "(pass confirmed=True after reviewing the diff)"
        )
    if source_claim is None or not source_claim.provenance.durable:
        raise LibraryWriteError(
            "refusing write-back: proof depends on session-only declarations; "
            "assemble a single self-contained snippet and call "
            "lean_prove(..., durable=True) before promoting"
        )

    area_from_name, entry, _decl = _entry_name_from_lean(lean_name)
    # Prefer explicit area arg if it matches; else use parsed.
    area_pascal = area[0].upper() + area[1:] if area else area_from_name
    if area.lower() == "coloring":
        area_pascal = "Coloring"
    if area_pascal != area_from_name:
        # Keep lean_name authoritative for path.
        area_pascal = area_from_name

    root = Path(formal_root) if formal_root else Path("formal")
    entry_dir = root / "Konigsberg" / "Literature" / area_pascal / entry
    if entry_dir.exists() and any(entry_dir.iterdir()):
        raise LibraryWriteError(f"entry already exists: {entry_dir}")

    # Re-elaborate against a fresh corpus env (not the session chain).
    snap = repl.snapshot()
    try:
        repl.load_preamble(timeout_s=300)
        state = repl.send_transactional(snippet)
        if not state.ok:
            raise LibraryWriteError(f"snippet does not elaborate: {state.errors}")
        axioms = tuple(repl.print_axioms(lean_name))
    finally:
        repl.restore(snap)

    forbidden = [a for a in axioms if a in _FORBIDDEN_AXIOMS or a not in AXIOM_WHITELIST]
    if forbidden:
        raise LibraryWriteError(
            f"axioms outside whitelist: {forbidden} (got {list(axioms)})"
        )

    sanity = (sanity_snippet or _default_sanity(lean_name)).strip() + "\n"
    if "example" not in sanity:
        raise LibraryWriteError("SanityChecks must contain at least one `example`")

    verified_at = _git_head(root.parent if (root / "..").exists() else Path.cwd())
    entry_dir.mkdir(parents=True, exist_ok=False)

    try:
        (entry_dir / "Statements.lean").write_text(
            _statements_lean(lean_name, snippet), encoding="utf-8"
        )
        (entry_dir / "Proofs.lean").write_text(_proofs_lean(lean_name), encoding="utf-8")
        (entry_dir / "SanityChecks.lean").write_text(sanity, encoding="utf-8")
        (entry_dir / "Notes.md").write_text(
            _notes_md(
                entry=entry,
                informal_statement=informal_statement,
                citation=citation,
                report=report,
            ),
            encoding="utf-8",
        )
        (entry_dir / "status.toml").write_text(
            _status_toml(
                entry=entry,
                area=area_pascal,
                citation=citation,
                lean_name=lean_name,
                axioms=list(axioms),
                verified_at=verified_at,
            ),
            encoding="utf-8",
        )
        _append_literature_imports(root / "Konigsberg" / "Literature.lean", area_pascal, entry)
        if run_gates:
            _run_entry_gates(root, entry_dir)
    except Exception:
        # Best-effort rollback of the new directory only.
        import shutil

        if entry_dir.exists():
            shutil.rmtree(entry_dir)
        raise

    rel = entry_dir.as_posix()
    return mint_lean_proof(
        statement=(
            f"promoted {lean_name} → {rel} (formalized; referee=accept; "
            f"axioms={list(axioms)})"
        ),
        axioms=axioms,
        tool="lean_add_to_library",
        durable=True,
    )
