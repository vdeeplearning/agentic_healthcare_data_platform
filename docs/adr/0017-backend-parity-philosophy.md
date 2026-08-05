# ADR 0017: Define parity by observable semantics

- Status: Accepted
- Date: 2026-08-05

## Context
SQLite and PostgreSQL use different types, planners, catalogs, and timeout mechanisms.
## Problem
Byte-for-byte physical equality is impossible and unnecessary, while loose “similarity” can hide analytical drift.
## Alternatives considered
- Compare physical schemas exactly: rejects valid engine differences.
- Test each engine independently: misses cross-engine divergence.
- Normalize observable semantics: strict where users and safety depend on it.
## Decision
Require equivalent catalogs, normalized rows/nulls/numerics, curated results, safety decisions, row limits, timeouts, provenance, and snapshot lineage. Permit different query plans and physical types.
## Consequences
Backend adapters normalize engine details into shared models.
## Tradeoffs
Floating-point and planner details need deliberate normalization and tolerances where applicable.
## Future implications
Lake gold snapshots must satisfy semantic parity before serving publication; distributed execution cannot bypass these contracts.
