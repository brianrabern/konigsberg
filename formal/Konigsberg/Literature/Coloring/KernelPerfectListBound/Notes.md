# KernelPerfectListBound

## Book
`\label{KernelPerfectListBound}`: If L is a list assignment on a kernel-perfect
oriented graph G such that |L(v)| > d⁺(v) for all v, then G is L-colorable.

## Fidelity review
Uses `Orientation.KernelPerfect` and `outDegree` from WP0 Kernel.lean; conclusion
is `ListColorable` (same as SecondListBound). Strict inequality `|L| > d⁺` matches
the book (not ≥). Quantifiers: all vertices, fixed orientation.

## Machinery needed for a real proof
Kernel existence on `C_L(c)`, induction on |V|, induced kernel-perfectness.
