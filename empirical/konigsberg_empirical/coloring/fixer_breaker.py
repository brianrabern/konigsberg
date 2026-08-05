"""FixerBreaker: fixer-breaker game solver for online / list choosability.

Ported from Landon Rabern's WebGraphs SuperSlimMind + SuperSlimSwapAnalyzer.
Validated against MindTests.cs fingerprints (TotalBoards + win verdicts).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..core import Graph
from .bit_assignments import MASK64, generate_assignments

__all__ = [
    "SuperSlimBoard",
    "SuperSlimMind",
    "Template",
    "load_dotgraph",
    "solve",
    "template_from_labels",
]


# --- Template / .graph I/O --------------------------------------------------

@dataclass(frozen=True)
class Template:
    sizes: list[int]


def load_dotgraph(path: str | Path) -> tuple[Graph, list[int]]:
    """Load a WebGraphs `.graph` JSON file → (Graph, vertex labels)."""
    data = json.loads(Path(path).read_text())
    vertices = data["Vertices"]
    n = len(vertices)
    labels = [int(v["Label"]) for v in vertices]
    edges = [
        (int(e["IndexV1"]), int(e["IndexV2"]))
        for e in data["Edges"]
        if int(e.get("Multiplicity", 1)) > 0
    ]
    return Graph.of(n, edges), labels


def template_from_labels(graph: Graph, labels: list[int]) -> tuple[Template, int]:
    """MindTests derivation: pot = max label; size[v] = pot + deg(v) − label[v]."""
    if len(labels) != graph.n:
        raise ValueError(f"labels length {len(labels)} != n={graph.n}")
    pot_size = max(labels) if labels else 0
    sizes = [pot_size + graph.degree(v) - labels[v] for v in range(graph.n)]
    return Template(sizes=sizes), pot_size


# --- bit helpers ------------------------------------------------------------

def _popcount(x: int) -> int:
    return x.bit_count()


def _get_bits(x: int) -> list[int]:
    """Single-bit masks, LSB first — port of ulong.GetBits."""
    bits: list[int] = []
    while x:
        lsb = x & -x
        bits.append(lsb)
        x ^= lsb
    return bits


# --- SuperSlimBoard ---------------------------------------------------------

class SuperSlimBoard:
    """Color-incidence trace. Matches WebGraphs SuperSlimBoard constructors."""

    __slots__ = ("_hash", "_length", "_stack_count", "_stacks", "_trace")

    def __init__(self, trace: list[int], stack_count: int) -> None:
        # From Generate: keep as-is (C# SuperSlimBoard(ulong[], int)).
        self._trace = list(trace)
        self._length = len(self._trace)
        self._stack_count = stack_count
        self._hash = _board_hash(self._trace, self._length)
        self._stacks: list[int] | None = None

    @classmethod
    def from_swap(
        cls, trace: list[int], i: int, j: int, swap: int, stack_count: int
    ) -> SuperSlimBoard:
        """Port of SuperSlimBoard(trace, i, j, swap, stackCount): XOR + drop 0 + insert-sort."""
        board = object.__new__(cls)
        new_trace: list[int] = []
        length = 0
        for k, raw in enumerate(trace):
            v = (raw ^ swap) if k in (i, j) else raw
            if v > 0:
                q = length
                while q > 0 and new_trace[q - 1] > v:
                    q -= 1
                new_trace.insert(q, v)
                length += 1
        # Pad/truncate to length (C# keeps _trace sized to original but _length tracks used).
        board._trace = new_trace
        board._length = length
        board._stack_count = stack_count
        board._hash = _board_hash(board._trace, board._length)
        board._stacks = None
        return board

    @property
    def stacks(self) -> list[int]:
        if self._stacks is None:
            s = [0] * self._stack_count
            for c in range(self._length):
                bits = self._trace[c]
                while bits:
                    lsb = bits & -bits
                    v = lsb.bit_length() - 1
                    if v < self._stack_count:
                        s[v] |= 1 << c
                    bits ^= lsb
            self._stacks = s
        return self._stacks

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SuperSlimBoard):
            return False
        if self._length != other._length:
            return False
        for i in range(self._length):
            if self._trace[i] != other._trace[i]:
                return False
        return True


def _board_hash(trace: list[int], length: int) -> int:
    h = 0
    for i in range(length):
        h = (h * 1000003) ^ (trace[i] & MASK64)
    return h & 0xFFFFFFFF


# --- partitions / swap analyzer ---------------------------------------------

_partitions_cache: dict[int, list[list[list[int]]]] = {}


def _get_partitions(count: int) -> list[list[list[int]]]:
    """Port of BranchGenerator.GetPartitions — perfect matchings (+ singleton if odd)."""
    if count in _partitions_cache:
        return _partitions_cache[count]
    parts = list(_enumerate_partitions_n(count))
    _partitions_cache[count] = parts
    return parts


def _enumerate_partitions_n(n: int):
    if n % 2 == 0:
        yield from _enumerate_partitions_list(list(range(n)))
    else:
        for i in range(n):
            rest = [j for j in range(n) if j != i]
            for partition in _enumerate_partitions_list(rest):
                yield [[i]] + partition


def _enumerate_partitions_list(indices: list[int]):
    if not indices:
        yield []
        return
    indices = list(indices)
    first = indices.pop(0)
    for i in range(len(indices)):
        partner = indices.pop(i)
        part = [first, partner]
        for partition in _enumerate_partitions_list(indices):
            yield partition + [part]
        indices.insert(i, partner)
    indices.insert(0, first)


class _SwapAnalyzer:
    """Port of SuperSlimSwapAnalyzer (SingleSwap / MultiSwap, non-proof mode)."""

    def __init__(self, swap_mode: str = "single_swap") -> None:
        self.swap_mode = swap_mode
        self._breaker_cache: dict[int, list[list[int]]] = {}

    def analyze(self, board: SuperSlimBoard, won_boards: set[SuperSlimBoard]) -> bool:
        for i in range(board._length):
            for j in range(i + 1, board._length):
                swappable = board._trace[i] ^ board._trace[j]
                always = True
                for breaker_choice in self._breaker_choices(swappable):
                    found = False
                    for response in self._fixer_responses(breaker_choice):
                        if self.swap_mode == "single_swap" and _popcount(response) > 2:
                            continue
                        child = SuperSlimBoard.from_swap(
                            board._trace, i, j, response, board._stack_count
                        )
                        if child in won_boards:
                            found = True
                            break
                    if not found:
                        always = False
                        break
                if always:
                    return True
        return False

    def _fixer_responses(self, possible_moves: list[int]) -> list[int]:
        # subset=0 skipped (C# starts at 1)
        n = len(possible_moves)
        out: list[int] = []
        for subset in range(1, 1 << n):
            response = 0
            x = subset
            while x:
                lsb = x & -x
                bit_idx = lsb.bit_length() - 1
                response |= possible_moves[bit_idx]
                x ^= lsb
            out.append(response)
        return out

    def _breaker_choices(self, swappable: int) -> list[list[int]]:
        if swappable in self._breaker_cache:
            return self._breaker_cache[swappable]
        bits = _get_bits(swappable)
        partitions = _get_partitions(len(bits))
        choices: list[list[int]] = []
        for partition in partitions:
            choice: list[int] = []
            for part in partition:
                x = 0
                for idx in part:
                    x |= bits[idx]
                choice.append(x)
            choices.append(choice)
        self._breaker_cache[swappable] = choices
        return choices


# --- SuperSlimMind ----------------------------------------------------------

class SuperSlimMind:
    """Port of WebGraphs SuperSlimMind.Analyze."""

    def __init__(
        self,
        graph: Graph,
        *,
        proof_finding: bool = False,
        swap_mode: str = "single_swap",
        reduction_mode: str = "none",
    ) -> None:
        self.graph = graph
        self.proof_finding = proof_finding
        self.swap_mode = swap_mode
        self.reduction_mode = reduction_mode
        self.min_pot = 0
        self.max_pot = 0
        self.only_consider_nearly_colorable_boards = False
        self.missing_edge_index = -1
        self.total_boards = 0
        self.board_counts: list[int] = []
        self._edges = sorted(graph.edges)
        self._line_adj = _line_graph_adj(self._edges)
        self._swap = _SwapAnalyzer(swap_mode)

    def analyze(self, template: Template) -> bool:
        remaining: list[SuperSlimBoard] = []
        fixer_won: set[SuperSlimBoard] = set()
        breaker_won: list[SuperSlimBoard] = []
        nearly_colorable: list[SuperSlimBoard] = []
        self.board_counts = []

        minimum = max(self.min_pot, max(template.sizes) if template.sizes else 0)
        maximum = min(self.max_pot, sum(template.sizes))
        for color_count in range(minimum, maximum + 1):
            for trace in generate_assignments(template.sizes, color_count):
                remaining.append(SuperSlimBoard(trace, len(template.sizes)))
        self.total_boards = len(remaining)

        # Colorable boards → fixer already won.
        colorable: list[SuperSlimBoard] = []
        for i in range(len(remaining) - 1, -1, -1):
            b = remaining[i]
            if self._is_colorable(b):
                remaining.pop(i)
                fixer_won.add(b)
                colorable.append(b)
        self.board_counts.append(len(colorable))

        # Nearly-colorable classification (used when the restricted mode is on).
        if self.only_consider_nearly_colorable_boards:
            for b in remaining:
                if self._nearly_colorable(b):
                    nearly_colorable.append(b)

        # Game fixpoint via swaps.
        while remaining:
            won_this_round: list[SuperSlimBoard] = []
            for i in range(len(remaining) - 1, -1, -1):
                b = remaining[i]
                if self._swap.analyze(b, fixer_won):
                    remaining.pop(i)
                    won_this_round.append(b)
            if won_this_round:
                self.board_counts.append(len(won_this_round))
                fixer_won.update(won_this_round)
            else:
                self.board_counts.append(0)
                break

        leftover = list(dict.fromkeys(breaker_won + remaining))  # preserve order, unique
        if self.only_consider_nearly_colorable_boards:
            nearly_set = set(nearly_colorable)
            leftover = [b for b in leftover if b in nearly_set]
        return len(leftover) <= 0

    def _edge_color_list(self, board: SuperSlimBoard, e: int) -> int:
        u, v = self._edges[e]
        stacks = board.stacks
        return stacks[u] & stacks[v]

    def _is_colorable(self, board: SuperSlimBoard) -> bool:
        lists = [self._edge_color_list(board, e) for e in range(len(self._edges))]
        return _line_choosable(lists, self._line_adj)

    def _nearly_colorable(self, board: SuperSlimBoard) -> bool:
        """Strict nearly-colorable: all edge lists nonempty, and colorable after
        deleting some (or the designated) edge.

        Boards whose only near-colorability comes from deleting an edge with an
        empty list are excluded — they are missing a color, not nearly colorable.
        See docs/handoff/NEARLY_COLORABLE_ADJUDICATION.md.
        """
        if not self._all_edge_lists_nonempty(board):
            return False
        if self.missing_edge_index >= 0:
            return self._colorable_without_edge(board, self.missing_edge_index)
        return any(
            self._colorable_without_edge(board, e) for e in range(len(self._edges))
        )

    def _all_edge_lists_nonempty(self, board: SuperSlimBoard) -> bool:
        return all(
            self._edge_color_list(board, e) != 0 for e in range(len(self._edges))
        )

    def _colorable_without_edge(self, board: SuperSlimBoard, edge_index: int) -> bool:
        """True iff the line graph is list-colorable with `edge_index` deleted."""
        lists = [self._edge_color_list(board, e) for e in range(len(self._edges))]
        return _line_choosable_skip(lists, self._line_adj, edge_index)


def _line_graph_adj(edges: list[tuple[int, int]]) -> list[list[int]]:
    m = len(edges)
    adj: list[list[int]] = [[] for _ in range(m)]
    for i in range(m):
        u, v = edges[i]
        for j in range(i + 1, m):
            x, y = edges[j]
            if u == x or u == y or v == x or v == y:
                adj[i].append(j)
                adj[j].append(i)
    return adj


def _line_choosable(lists: list[int], adj: list[list[int]]) -> bool:
    return _line_choosable_skip(lists, adj, skip=-1)


def _line_choosable_skip(lists: list[int], adj: list[list[int]], skip: int) -> bool:
    """List-color the line graph, optionally skipping one edge-vertex."""
    later = [[j for j in neigh if j > i] for i, neigh in enumerate(adj)]
    n = len(lists)

    def rec(v: int, assignment: list[int]) -> bool:
        if v >= n:
            return True
        if v == skip:
            return rec(v + 1, assignment)
        colors = assignment[v]
        while colors:
            color = colors & -colors
            nxt = list(assignment)
            for w in later[v]:
                if w != skip:
                    nxt[w] &= ~color
            if rec(v + 1, nxt):
                return True
            colors ^= color
        return False

    return rec(0, list(lists))


def solve(graph: Graph, list_sizes: list[int]) -> bool:
    mind = SuperSlimMind(graph)
    mind.max_pot = max(list_sizes) if list_sizes else 0
    return mind.analyze(Template(sizes=list(list_sizes)))
