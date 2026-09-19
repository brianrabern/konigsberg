"""Interactive session state + JSONL persistence (Claude-Code-shaped).

One Session = one investigation: normalized message history + the epistemic
Ledger. SessionStore appends every event under ``~/.konigsberg/sessions/<id>.jsonl``
so ``--resume`` / ``--continue`` restore history **and** the exact trust state
(claims are replayed, never re-derived).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .ledger import (
    Claim,
    EvidenceKind,
    Ledger,
    Provenance,
    TrustRoot,
)
from .lemmas import LemmaNotebook, LockedLemma, lemma_has_hole
from .models import (
    AssistantText,
    HistoryItem,
    ToolCall,
    ToolResultMsg,
    UserMsg,
)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def default_sessions_dir() -> Path:
    return Path.home() / ".konigsberg" / "sessions"


# --- serialization --------------------------------------------------------


def claim_to_dict(claim: Claim) -> dict[str, Any]:
    p = claim.provenance
    return {
        "statement": claim.statement,
        "provenance": {
            "trust_root": p.trust_root.value,
            "evidence_kind": p.evidence_kind.value,
            "well_formed": p.well_formed,
            "bound": p.bound,
            "axioms": list(p.axioms),
            "tool": p.tool,
            "at": p.at,
            "durable": p.durable,
        },
    }


def claim_from_dict(data: dict[str, Any]) -> Claim:
    p = data["provenance"]
    return Claim(
        statement=data["statement"],
        provenance=Provenance(
            trust_root=TrustRoot(p["trust_root"]),
            evidence_kind=EvidenceKind(p["evidence_kind"]),
            well_formed=bool(p["well_formed"]),
            bound=p.get("bound"),
            axioms=tuple(p.get("axioms") or ()),
            tool=p.get("tool") or "",
            at=p.get("at") or _utcnow(),
            durable=bool(p.get("durable", False)),
        ),
    )


def history_item_to_dict(item: HistoryItem) -> dict[str, Any]:
    if isinstance(item, UserMsg):
        return {"kind": "user", "text": item.text}
    if isinstance(item, AssistantText):
        return {"kind": "assistant", "text": item.text}
    if isinstance(item, ToolCall):
        return {"kind": "tool_call", "id": item.id, "name": item.name, "args": item.args}
    if isinstance(item, ToolResultMsg):
        return {
            "kind": "tool_result",
            "id": item.id,
            "content": item.content,
            "is_error": item.is_error,
        }
    raise TypeError(f"unknown history item: {type(item)!r}")


def history_item_from_dict(data: dict[str, Any]) -> HistoryItem:
    kind = data["kind"]
    if kind == "user":
        return UserMsg(data["text"])
    if kind == "assistant":
        return AssistantText(data["text"])
    if kind == "tool_call":
        return ToolCall(id=data["id"], name=data["name"], args=dict(data.get("args") or {}))
    if kind == "tool_result":
        return ToolResultMsg(
            id=data["id"],
            content=data["content"],
            is_error=bool(data.get("is_error", False)),
        )
    raise ValueError(f"unknown history kind: {kind!r}")


@dataclass
class Session:
    """Durable investigation state: chat history + ledger + locked lemmas."""

    id: str
    history: list[HistoryItem] = field(default_factory=list)
    ledger: Ledger = field(default_factory=Ledger)
    notebook: LemmaNotebook = field(default_factory=LemmaNotebook)
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)

    @classmethod
    def create(cls, session_id: str | None = None) -> Session:
        return cls(id=session_id or uuid.uuid4().hex[:12])

    def touch(self) -> None:
        self.updated_at = _utcnow()


class SessionStore:
    """Append-only JSONL session log under ``~/.konigsberg/sessions/``."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_sessions_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, session_id: str) -> Path:
        return self.root / f"{session_id}.jsonl"

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.jsonl"))

    def _has_content(self, session_id: str) -> bool:
        """True if the session has any event beyond the initial session_meta —
        i.e. it isn't a freshly-created empty session."""
        path = self.path_for(session_id)
        if not path.exists():
            return False
        n = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                n += 1
                if n > 1:
                    return True
        return False

    def latest_id(self, *, with_content: bool = False) -> str | None:
        paths = list(self.root.glob("*.jsonl"))
        if with_content:
            paths = [p for p in paths if self._has_content(p.stem)]
        if not paths:
            return None
        return max(paths, key=lambda p: p.stat().st_mtime).stem

    def write_event(self, session_id: str, event: dict[str, Any]) -> None:
        """Append one JSONL event (does not mutate Session)."""
        payload = {**event, "at": event.get("at") or _utcnow()}
        with self.path_for(session_id).open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def create(self, session: Session | None = None) -> Session:
        sess = session or Session.create()
        self.write_event(
            sess.id,
            {"type": "session_meta", "id": sess.id, "created_at": sess.created_at},
        )
        return sess

    def log_user(self, session: Session, text: str) -> None:
        session.history.append(UserMsg(text))
        session.touch()
        self.write_event(session.id, {"type": "user", "text": text})

    def log_history_item(self, session: Session, item: HistoryItem) -> None:
        """Append to session.history and persist."""
        session.history.append(item)
        session.touch()
        d = history_item_to_dict(item)
        d["type"] = d.pop("kind")
        self.write_event(session.id, d)

    def log_claim(self, session: Session, claim: Claim) -> None:
        session.ledger.record(claim)
        session.touch()
        self.write_event(session.id, {"type": "claim", **claim_to_dict(claim)})

    def log_lemma(self, session: Session, lemma: LockedLemma) -> None:
        """Lock a proved snippet on the working notebook (append-only JSONL)."""
        if lemma_has_hole(lemma):
            return
        session.notebook.lock(lemma)
        session.touch()
        self.write_event(session.id, {"type": "lemma", **lemma.to_dict()})

    def log_compaction(
        self, session: Session, *, summary: str, kept: list[HistoryItem]
    ) -> None:
        """Rewrite history in memory + record compact event. Ledger untouched."""
        session.history = [UserMsg(summary), *kept]
        session.touch()
        self.write_event(
            session.id,
            {
                "type": "compact",
                "summary": summary,
                "kept": [history_item_to_dict(i) for i in kept],
            },
        )

    def load(self, session_id: str) -> Session:
        path = self.path_for(session_id)
        if not path.exists():
            raise FileNotFoundError(f"no session {session_id!r} at {path}")
        session = Session(id=session_id)
        history: list[HistoryItem] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            et = event["type"]
            if et == "session_meta":
                session.created_at = event.get("created_at") or session.created_at
                session.id = event.get("id") or session_id
            elif et == "user":
                history.append(UserMsg(event["text"]))
            elif et == "assistant":
                history.append(AssistantText(event["text"]))
            elif et == "tool_call":
                history.append(
                    ToolCall(
                        id=event["id"],
                        name=event["name"],
                        args=dict(event.get("args") or {}),
                    )
                )
            elif et == "tool_result":
                history.append(
                    ToolResultMsg(
                        id=event["id"],
                        content=event["content"],
                        is_error=bool(event.get("is_error", False)),
                    )
                )
            elif et == "claim":
                # Reconstruct trust state from recorded claims — never re-run tools.
                session.ledger.record(claim_from_dict(event))
            elif et == "lemma":
                lemma = LockedLemma.from_dict(event)
                if not lemma_has_hole(lemma):
                    session.notebook.lock(lemma)
            elif et == "compact":
                kept = [history_item_from_dict(i) for i in event.get("kept") or []]
                history = [UserMsg(event["summary"]), *kept]
            else:
                raise ValueError(f"unknown session event type: {et!r}")
            if event.get("at"):
                session.updated_at = event["at"]
        session.history = history
        return session

    def latest(self) -> Session | None:
        # Skip the empty session Repl.__init__ just created, so --continue lands
        # on the newest session that actually has content.
        sid = self.latest_id(with_content=True)
        return self.load(sid) if sid else None
