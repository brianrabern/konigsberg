"""Exact-arithmetic graph polynomial — faithful port of WebGraphs
Choosability/Polynomials/{GraphPolynomial,Normalizer,SignLookup,FactoredRational,PrimeNumbers}.cs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import Graph

# --- PrimeNumbers -----------------------------------------------------------

_PRIMES: list[int] = [2, 3, 5, 7, 11, 13, 17, 19]


def _prime(i: int) -> int:
    if i >= len(_PRIMES):
        _compute_more_primes(i)
    return _PRIMES[i]


def _compute_more_primes(i: int) -> None:
    m = max(i, 2 * len(_PRIMES))
    p = _PRIMES[-1] + 2
    while len(_PRIMES) <= m:
        if _is_prime(p):
            _PRIMES.append(p)
        p += 2


def _is_prime(p: int) -> bool:
    k = 0
    while _PRIMES[k] * _PRIMES[k] <= p:
        if p % _PRIMES[k] == 0:
            return False
        k += 1
    return True


def _int_power(p: int, k: int) -> int:
    """Integer power by successive squaring — matches FactoredRational.Power."""
    m = 1
    while k > 0:
        e = 1
        n = p
        while e <= (k >> 1):
            n *= n
            e <<= 1
        k -= e
        m *= n
    return m


# --- FactoredRational -------------------------------------------------------

@dataclass
class FactoredRational:
    """Prime-exponent rational with a sign. Sign == 0 is zero."""

    sign: int = 1
    k: list[int] = field(default_factory=list)

    @staticmethod
    def from_int(n: int) -> FactoredRational:
        sign = 0 if n == 0 else (1 if n > 0 else -1)
        n = abs(n)
        exponents: list[int] = []
        i = 0
        while n > 1:
            exponents.append(0)
            p = _prime(i)
            while n % p == 0:
                exponents[i] += 1
                n //= p
            i += 1
        return FactoredRational(sign=sign, k=exponents)

    def __mul__(self, other: FactoredRational) -> FactoredRational:
        sign = self.sign * other.sign
        exponents: list[int] = []
        if sign != 0:
            m = max(len(self.k), len(other.k))
            for i in range(m):
                e = 0
                if i < len(self.k):
                    e += self.k[i]
                if i < len(other.k):
                    e += other.k[i]
                exponents.append(e)
        return FactoredRational(sign=sign, k=exponents)

    def __truediv__(self, other: FactoredRational) -> FactoredRational:
        sign = self.sign * other.sign
        exponents: list[int] = []
        if sign != 0:
            m = max(len(self.k), len(other.k))
            for i in range(m):
                e = 0
                if i < len(self.k):
                    e += self.k[i]
                if i < len(other.k):
                    e -= other.k[i]
                exponents.append(e)
        return FactoredRational(sign=sign, k=exponents)

    def to_rational(self) -> tuple[int, int]:
        # Empty K with Sign≠0 is 1 (no prime factors). Only Sign==0 is zero.
        # Matches FactoredRational.ToRational: null K or Sign==0 → 0.
        if self.sign == 0:
            return 0, 1
        top = self.sign
        bottom = 1
        for i, e in enumerate(self.k):
            if e > 0:
                top *= _int_power(_prime(i), e)
            elif e < 0:
                bottom *= _int_power(_prime(i), -e)
        return top, bottom


ZERO = FactoredRational(sign=0, k=[])
FactoredRational.ZERO = ZERO  # type: ignore[attr-defined]

# --- Normalizer / SignLookup ------------------------------------------------

class Normalizer:
    def __init__(self, height: list[int]) -> None:
        m = max(height) if height else 0
        self.factored_difference: list[list[FactoredRational]] = [
            [FactoredRational.from_int(i - j) for j in range(m + 1)] for i in range(m + 1)
        ]
        n = len(height)
        self.inside_product: list[list[FactoredRational]] = [
            [FactoredRational(sign=1, k=[]) for _ in range(m + 1)] for _ in range(n)
        ]
        for i in range(n):
            for j in range(height[i] + 1):
                prod = FactoredRational(sign=1, k=[])
                for kk in range(height[i] + 1):
                    if kk == j:
                        continue
                    prod = prod * self.factored_difference[j][kk]
                self.inside_product[i][j] = prod

    def get(self, a: list[int]) -> FactoredRational:
        normalizer = FactoredRational(sign=1, k=[])
        for i, ai in enumerate(a):
            normalizer = normalizer * self.inside_product[i][ai]
        return normalizer


class SignLookup:
    def __init__(self, height: list[int]) -> None:
        m = max(height) if height else 0
        self.sign: list[list[int]] = [
            [0 if i == j else (1 if i > j else -1) for j in range(m + 1)]
            for i in range(m + 1)
        ]


# --- GraphPolynomial --------------------------------------------------------

def _prior_neighbors(graph: Graph) -> list[list[int]]:
    prior: list[list[int]] = [[] for _ in range(graph.n)]
    for u, v in graph.edges:
        if u < v:
            prior[v].append(u)
        else:
            prior[u].append(v)
    for w in range(graph.n):
        prior[w].sort()
    return prior


def _gcd(x: int, y: int) -> int:
    x, y = abs(x), abs(y)
    while x > 0:
        x, y = y % x, x
    return y


def graph_polynomial_coefficient(graph: Graph, power: list[int]) -> int:
    """Coefficient of ∏ x_v^{power[v]} in P_G = ∏_{uv∈E,u<v} (x_u − x_v).

    Port of GraphPolynomial.GetCoefficient.
    """
    if len(power) != graph.n:
        raise ValueError(f"power length {len(power)} != n={graph.n}")
    prior = _prior_neighbors(graph)
    normalizer = Normalizer(power)
    a = [0] * len(power)
    top, bottom = 0, 1
    partial = FactoredRational(sign=1, k=[])

    def sum_terms(w: int) -> None:
        nonlocal top, bottom, partial
        if w == len(power):
            r = partial / normalizer.get(a)
            top2, bottom2 = r.to_rational()
            top = top * bottom2 + bottom * top2
            bottom = bottom * bottom2
            g = _gcd(top, bottom)
            top //= g
            bottom //= g
            return
        for j in range(power[w] + 1):
            a[w] = j
            current = FactoredRational(sign=1, k=[])
            for v in prior[w]:
                current = current * normalizer.factored_difference[a[v]][a[w]]
            if current.sign == 0:
                continue
            partial = partial * current
            sum_terms(w + 1)
            partial = partial / current

    sum_terms(0)
    return top // bottom


def sign_sum(graph: Graph, power: list[int]) -> int:
    """Port of GraphPolynomial.GetSignSum."""
    if len(power) != graph.n:
        raise ValueError(f"power length {len(power)} != n={graph.n}")
    prior = _prior_neighbors(graph)
    lookup = SignLookup(power)
    a = [0] * len(power)
    total = 0
    partial = 1

    def sum_signs(w: int) -> None:
        nonlocal total, partial
        if w == len(power):
            total += partial
            return
        for j in range(power[w] + 1):
            a[w] = j
            current = 1
            for v in prior[w]:
                current *= lookup.sign[a[v]][a[w]]
            if current == 0:
                continue
            partial *= current
            sum_signs(w + 1)
            partial //= current

    sum_signs(0)
    return total
