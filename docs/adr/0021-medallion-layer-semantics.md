# ADR 0021: Raw, bronze, silver, and gold semantics
## Context
Versioned stages need meanings that remain stable when execution engines change.
## Problem
Unclear layers allow correction, parsing, validation, and aggregation to blur together.
## Alternatives considered
A single staging area, two layers, arbitrary pipeline names, and the four medallion layers were considered.
## Decision
Use exactly raw, bronze, silver, and gold with enforced adjacent transitions.
## Consequences
Each snapshot has a clear quality level and parent.
## Tradeoffs
More manifests and objects are retained than in an overwrite-in-place workflow.
## Future migration implications
Spark implementations must produce the same layer contracts and validation evidence.
