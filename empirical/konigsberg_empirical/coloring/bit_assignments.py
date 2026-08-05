"""Bit-level assignment enumeration — faithful port of
WebGraphs/BitLevelGeneration/{BitVectors,Assignments_type}.cs (ulong path).

This is what produces SuperSlimMind.TotalBoards. Match Generate bit-for-bit;
naive list-assignment enumeration will not hit the fingerprints.
"""
from __future__ import annotations

MASK64 = (1 << 64) - 1


def _u64_not(x: int) -> int:
    return (~x) & MASK64


def right_fill_to_msb(x: int) -> int:
    x &= MASK64
    x |= x >> 1
    x |= x >> 2
    x |= x >> 4
    x |= x >> 8
    x |= x >> 16
    x |= x >> 32
    return x & MASK64


def to_bit_vector(weights: list[int]) -> list[int]:
    """Pack per-vertex integers into bit-sliced ulong layers (BitVectors_ulong)."""
    v = list(weights)
    layers: list[int] = []
    while True:
        m = 0
        zero = True
        for i in range(len(v)):
            if v[i] != 0:
                zero = False
            if v[i] & 1:
                m |= 1 << i
            v[i] >>= 1
        layers.append(m & MASK64)
        if zero:
            break
    return layers


def _increment(n: list[int], m: int) -> None:
    m &= MASK64
    i = 0
    while m != 0:
        if i >= len(n):
            n.append(0)
        t1 = m & n[i]
        t2 = (m ^ n[i]) & MASK64
        m = t1
        n[i] = t2
        i += 1


def _decrement(n: list[int], m: int) -> None:
    m &= MASK64
    i = 0
    while m != 0:
        if i >= len(n):
            n.append(0)
        t1 = m & _u64_not(n[i])
        t2 = (m ^ n[i]) & MASK64
        m = t1
        n[i] = t2
        i += 1


def _zeroes(n: list[int]) -> int:
    m = 0
    for layer in n:
        m |= layer
    return _u64_not(m)


def _greater_than(n: list[int], k: list[int]) -> int:
    a = 0
    b = 0
    for i in range(max(len(n), len(k)) - 1, -1, -1):
        if i >= len(k):
            a |= n[i]
        elif i >= len(n):
            b |= k[i]
        else:
            a |= (_u64_not(b) & n[i] & _u64_not(k[i])) & MASK64
            b |= (_u64_not(a) & _u64_not(n[i]) & k[i]) & MASK64
    return (a & _u64_not(b)) & MASK64


def generate_assignments(sizes: list[int], pot_size: int) -> list[list[int]]:
    """Port of Assignments_ulong.Generate — list of color-incidence traces.

    Each trace is a list of pot_size ulongs; trace[c] has bit v set iff vertex v
    contains color c. Canonical under color permutation.
    """
    if pot_size <= 0:
        return []
    n = len(sizes)
    size_vector = to_bit_vector(sizes)
    assignments: list[list[int]] = []
    assignment = [0] * pot_size

    r: list[list[int]] = [
        to_bit_vector([pot_size - 1 - i] * n) for i in range(pot_size)
    ]
    care = _greater_than(size_vector, r[0])
    dont_care = _u64_not(care | _zeroes(size_vector))
    _generate(size_vector, assignments, assignment, r, 0, 1, care, dont_care)
    return assignments


def _generate(
    sizes: list[int],
    assignments: list[list[int]],
    assignment: list[int],
    r: list[list[int]],
    i: int,
    last: int,
    care: int,
    dont_care: int,
) -> None:
    g = (care & _u64_not(last)) & MASK64
    q = (_u64_not(care) & _u64_not(dont_care) & last) & MASK64

    if g > q:
        f = right_fill_to_msb(g)
        x = ((care & f) | (last & _u64_not(f))) & MASK64
    elif q > g:
        f = right_fill_to_msb(q)
        t = (_u64_not(f) & last) & MASK64
        y = (dont_care & _u64_not(f) & _u64_not(t)) & MASK64
        if y == 0:
            return
        y2 = (dont_care & t & (y | (y - 1))) & MASK64
        # y & -y : least significant set bit (C#: y & (0 - y) on ulong)
        x = ((care & (f >> 1)) | (t & _u64_not(y2)) | (y & -y)) & MASK64
    else:
        x = last & MASK64

    end = (care | dont_care) & MASK64
    if i >= len(assignment) - 1:
        while True:
            assignment[i] = x
            assignments.append(list(assignment))
            if x == end:
                break
            x = (((x - (care + dont_care)) & dont_care) + care) & MASK64
    else:
        while True:
            assignment[i] = x
            _decrement(sizes, x)
            c = _greater_than(sizes, r[i + 1])
            z = _zeroes(sizes)
            if (c & z) == 0:
                dc = _u64_not(c | z)
                _generate(sizes, assignments, assignment, r, i + 1, x, c, dc)
            _increment(sizes, x)
            if x == end:
                break
            x = (((x - (care + dont_care)) & dont_care) + care) & MASK64
