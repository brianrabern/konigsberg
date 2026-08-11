# BrooksListForm

## Informal statement
A connected graph is degree-choosable iff it is not a Gallai tree (Erdős–Rubin–Taylor / list Brooks).

## Source
Book §Brooks' theorem for list coloring (section stub); standard ERT characterization.

## Provenance
Agent-drafted stated target; human fidelity read. Distinct from EXTERNAL chromatic BrooksLean.

## Fidelity review
Gallai tree = connected + every block is complete or odd cycle (`IsGallaiTree`).
`DegreeChoosable` = `FChoosable` at `f = degree` (Areas/Basic). Connected
hypothesis matches the classical statement.

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
