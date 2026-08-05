# ADR 0027: JSON Lines for the local lake foundation
## Context
The first lake adapter needs transparent, dependency-light files.
## Problem
Parquet would add PyArrow and binary inspection before columnar performance is needed.
## Alternatives considered
CSV, JSON arrays, JSON Lines, and Parquet were considered.
## Decision
Use canonical JSON Lines for all four local layers in this milestone.
## Consequences
Files are streamable, diffable in tests, and require no new dependency.
## Tradeoffs
Storage size and analytical scan speed are worse than Parquet.
## Future migration implications
Format-specific code remains isolated; a future Parquet adapter requires an ADR and JSONL fallback fixtures.
