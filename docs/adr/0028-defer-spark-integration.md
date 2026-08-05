# ADR 0028: Defer Spark integration
## Context
The contracts now identify every deterministic transformation and output.
## Problem
Spark adds JVM, partitioning, shuffle, cluster, and packaging choices unrelated to current semantic proof.
## Alternatives considered
Add PySpark now, replace local transforms, or defer execution-engine work.
## Decision
Defer Spark until the local contracts and lineage are stable and verified.
## Consequences
This milestone remains locally reproducible.
## Tradeoffs
It does not demonstrate distributed scale.
## Future migration implications
The next milestone should implement contract-compatible PySpark transforms and parity tests against local Python.
