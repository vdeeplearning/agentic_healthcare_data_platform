# ADR 0019: Preserve logical equivalence while allowing physical differences

- Status: Accepted
- Date: 2026-08-05

## Context
PostgreSQL has native dates, identity columns, schemas, server timeouts, and JSON explain plans; SQLite uses text dates, row IDs, files, and cooperative cancellation.
## Problem
Forcing identical DDL would misuse at least one engine, while redesigning PostgreSQL would change semantics.
## Alternatives considered
- Copy SQLite DDL literally: poor PostgreSQL fit.
- Redesign for PostgreSQL: breaks logical parity.
- Map physical types and controls while preserving entities, keys, constraints, views, and metrics.
## Decision
Use engine-appropriate physical DDL with the same logical model and record stream. Snapshot IDs differ by backend; dataset and manifest IDs remain shared.
## Consequences
Dates and numerics are normalized at the query boundary, and query plans remain backend-specific provenance.
## Tradeoffs
Some SQL functions are dialect-specific; central validation renders the selected dialect and planners receive the bounded dialect catalog.
## Future implications
Raw/bronze/silver/gold layers can remain logically governed while choosing appropriate physical formats; Spark and Parquet need not imitate database storage.
