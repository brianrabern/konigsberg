# HajnalLemma

## Book
`\label{HajnalLemma}`: If 𝒬 is a collection of maximum cliques, then
|⋃𝒬| + |⋂𝒬| ≥ 2ω(G).

## Fidelity review
`𝒬 ⊆ maxCliqueCollection G` ensures members are maximum cliques. Cardinality
sum uses Finset `biUnion` / `sInter`. Constant `2 * cliqueNum` matches ω(G).
