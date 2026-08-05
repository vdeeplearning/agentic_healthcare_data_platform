# ADR 0025: Gold snapshot is the parent of serving snapshots
## Context
Analytical answers already resolve through database snapshots and logical manifests.
## Problem
Without a gold parent, lineage stops before the transformation chain.
## Alternatives considered
Copying source IDs only, keeping unrelated graphs, and explicit gold-parent metadata were considered.
## Decision
SQLite and PostgreSQL serving snapshots record `gold_snapshot_id` and the raw source batch.
## Consequences
An audit can resolve from SQL execution back to raw source objects.
## Tradeoffs
Serving publication requires a validated active gold snapshot.
## Future migration implications
Additional serving systems must preserve this parent edge.
