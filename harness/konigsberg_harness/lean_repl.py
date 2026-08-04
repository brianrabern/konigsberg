"""Persistent Lean environment (LeanREPL-backed).

A persistent process, NOT a shell-out per snippet: keeps live elaboration state,
returns structured goal state, amortizes startup. This is a hard-to-change
contract (open decision #1) — evaluate LeanREPL vs alternatives before
committing.

Every call is isolated and TIMED. `decide` on a large SimpleGraph will hang; the
timeout is a correctness feature, not just hygiene. When a call times out the
process is KILLED, not left running: a hung elaboration leaves the environment in
an unknown state, so continuing against it would silently corrupt every later
result. Callers must `start()` again (or use `restart()`) after a timeout — the
live env is intentionally forfeit. Trading env state for the guarantee that we
never report against a corrupted environment is the whole point of the ledger.

Protocol
--------
Talks to leanprover-community/repl over stdin/stdout. Each request is a JSON
object; each response is a JSON object. We frame requests with a trailing blank
line (the REPL's convention) and read the reply by accumulating stdout until it
parses as one complete JSON value — robust to both blank-line-terminated and
bare-object framing.

Request shapes we use:
    {"cmd": "<lean source>", "env": <id?>}     # elaborate source in an env
    {"cmd": "#print axioms Foo", "env": <id>}  # ordinary command; info message

Response fields we read:
    env       int    — id of the environment AFTER this command; thread it on
    messages  list   — {severity: error|warning|info, data: str, pos, endPos}
    sorries   list   — {goal: str, proofState: int, pos, endPos}
    goals     list   — present for tactic-mode replies

Launch command defaults to `lake exe repl`, which builds+runs the `repl` exe
from the REPL package required in formal/lakefile.toml (pinned to its v4.31.0
branch so toolchains match). Override `repl_cmd` if you run a separately-cloned
REPL instead: ("lake", "env", "/path/to/repl/.lake/build/bin/repl").
"""
from __future__ import annotations

import json
import queue
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self

# Default: build+run the `repl` exe from the REPL package required in
# formal/lakefile.toml. `lake exe` runs it inside the project's Lake environment,
# so it sees the same toolchain and olean cache as `formal/` and imports resolve.
# Override `repl_cmd` if you instead run a separately-cloned REPL, e.g.
# ("lake", "env", "/path/to/repl/.lake/build/bin/repl").
DEFAULT_REPL_CMD: tuple[str, ...] = ("lake", "exe", "repl")

# Cap stderr retained for diagnostics so a chatty/looping process can't grow the
# buffer without bound.
_MAX_ERR_LINES = 200


class LeanREPLError(RuntimeError):
    """The REPL process failed, died, or produced an unparseable reply."""


class LeanREPLTimeout(TimeoutError):
    """A call exceeded its deadline. The process has been killed; env is gone."""


@dataclass
class GoalState:
    goals: list[str]
    errors: list[str]
    infos: list[str] = field(default_factory=list)
    env: int | None = None
    raw: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def _parse_axioms(text: str) -> list[str]:
    """Parse the axiom list from `#print axioms <name>` output.

    Handles the two shapes Lean emits:
        "<name> does not depend on any axioms"                       -> []
        "'<name>' depends on axioms: [propext, Classical.choice]"    -> [...]
    An unfinished proof surfaces here as `sorryAx`; `native_decide` as
    `Lean.ofReduceBool`. We do not filter — the axiom GATE decides; this only
    reports faithfully.
    """
    if "does not depend on any axioms" in text:
        return []
    m = re.search(r"\[(.*)\]", text, re.DOTALL)
    body = m.group(1) if m else text.split("axioms", 1)[-1].lstrip(": \n\t")
    return [tok for tok in re.split(r"[,\s]+", body.strip()) if tok]


def _to_goal_state(resp: dict) -> GoalState:
    """Map a raw REPL response dict onto GoalState. Pure; unit-tested."""
    messages = resp.get("messages", []) or []
    errors = [m.get("data", "") for m in messages if m.get("severity") == "error"]
    infos = [m.get("data", "") for m in messages if m.get("severity") == "info"]
    # Tactic replies carry `goals`; command replies expose open goals via sorries.
    goals = list(resp.get("goals", []) or [])
    if not goals:
        goals = [s["goal"] for s in resp.get("sorries", []) or [] if "goal" in s]
    return GoalState(
        goals=goals,
        errors=errors,
        infos=infos,
        env=resp.get("env"),
        raw=resp,
    )


class LeanREPL:
    def __init__(
        self,
        project_dir: str = "formal",
        timeout_s: float = 20.0,
        repl_cmd: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        self.project_dir = project_dir
        self.timeout_s = timeout_s
        self.repl_cmd = list(repl_cmd) if repl_cmd is not None else list(DEFAULT_REPL_CMD)

        self._proc: subprocess.Popen[str] | None = None
        self._out_q: queue.Queue[str | None] = queue.Queue()
        self._err_lines: list[str] = []
        self._env: int | None = None  # id of the current live environment

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        self._proc = subprocess.Popen(
            self.repl_cmd,
            cwd=self.project_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # line-buffered
        )
        self._out_q = queue.Queue()
        self._err_lines = []
        self._env = None
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()

    def restart(self) -> None:
        self.close()
        self.start()

    def close(self) -> None:
        self._kill()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- public API --------------------------------------------------------

    def send(
        self, snippet: str, *, timeout_s: float | None = None, new_env: bool = False
    ) -> GoalState:
        """Elaborate `snippet` against the live environment; return goals+errors.

        The current env id is sent WITH the command and the returned one is kept,
        so state is live (a `def` here is visible to a `theorem` next). Pass
        `new_env=True` to run in a fresh environment instead — required for
        `import` commands, which the REPL only accepts when no env is specified.
        On timeout the process is killed and LeanREPLTimeout is raised — see the
        module docstring.
        """
        payload: dict = {"cmd": snippet}
        if not new_env and self._env is not None:
            payload["env"] = self._env
        resp = self._request(payload, timeout_s)
        if "env" in resp:
            self._env = resp["env"]
        return _to_goal_state(resp)

    def print_axioms(self, lean_name: str, *, timeout_s: float | None = None) -> list[str]:
        """`#print axioms {lean_name}` -> parsed axiom list. Used by check_axioms.

        Runs in the current environment, so `lean_name` must already be defined
        there (elaborate its declaration first). Raises if the command errors
        (e.g. unknown identifier), rather than silently returning [].
        """
        state = self.send(f"#print axioms {lean_name}", timeout_s=timeout_s)
        if state.errors:
            raise LeanREPLError(
                f"#print axioms {lean_name} failed: {'; '.join(state.errors)}"
            )
        return _parse_axioms("\n".join(state.infos))

    # -- internals ---------------------------------------------------------

    def _request(self, payload: dict, timeout_s: float | None) -> dict:
        self._ensure_running()
        assert self._proc is not None and self._proc.stdin is not None
        deadline = time.monotonic() + (timeout_s if timeout_s is not None else self.timeout_s)
        try:
            self._proc.stdin.write(json.dumps(payload) + "\n\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, ValueError) as e:  # dead pipe / closed stdin
            self._kill()
            raise LeanREPLError(f"REPL stdin write failed: {e}\n{self._stderr()}") from e
        return self._read_response(deadline)

    def _read_response(self, deadline: float) -> dict:
        """Accumulate stdout lines until they parse as one complete JSON object.

        Returns as soon as a valid JSON value is assembled (handles both
        blank-line-terminated and bare-object framing). On deadline the process
        is killed.
        """
        lines: list[str] = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._kill()
                raise LeanREPLTimeout(
                    f"no complete reply within {self.timeout_s:g}s; process killed"
                )
            try:
                line = self._out_q.get(timeout=remaining)
            except queue.Empty:
                self._kill()
                raise LeanREPLTimeout(
                    f"no complete reply within {self.timeout_s:g}s; process killed"
                )
            if line is None:  # stdout closed => process exited
                raise LeanREPLError(f"REPL stdout closed unexpectedly\n{self._stderr()}")
            if not line.strip() and not lines:
                continue  # skip leading blank lines before a frame
            lines.append(line)
            buf = "".join(lines)
            try:
                obj = json.loads(buf)
            except json.JSONDecodeError:
                continue  # not a complete object yet
            if not isinstance(obj, dict):
                raise LeanREPLError(f"REPL reply was not a JSON object: {buf!r}")
            return obj

    def _pump_stdout(self, proc: subprocess.Popen | None = None) -> None:
        stream = (proc or self._proc).stdout  # type: ignore[union-attr]
        try:
            for line in stream:  # type: ignore[union-attr]
                self._out_q.put(line)
        finally:
            self._out_q.put(None)  # EOF sentinel

    def _pump_stderr(self) -> None:
        stream = self._proc.stderr if self._proc else None
        if stream is None:
            return
        for line in stream:
            self._err_lines.append(line)
            if len(self._err_lines) > _MAX_ERR_LINES:
                del self._err_lines[0]

    def _ensure_running(self) -> None:
        if self._proc is None or self._proc.poll() is not None:
            raise LeanREPLError("REPL is not running; call start() (or restart()) first")

    def _stderr(self) -> str:
        return "".join(self._err_lines).strip()

    def _kill(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        self._env = None


__all__ = [
    "GoalState",
    "LeanREPL",
    "LeanREPLError",
    "LeanREPLTimeout",
]
