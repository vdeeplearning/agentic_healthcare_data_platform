# ADR 0015: Keep SQLite as a permanent backend

- Status: Accepted
- Date: 2026-08-05

## Context
PostgreSQL is now an optional analytical backend, but the project already has a portable deterministic SQLite experience.
## Problem
Replacing SQLite would remove zero-configuration demos, the CI reference fixture, and the simplest rollback path.
## Alternatives considered
- Replace SQLite with PostgreSQL: operationally realistic but breaks portability.
- Treat SQLite as temporary: creates future compatibility ambiguity.
- Support both permanently: more tests, but preserves clear roles.
## Decision
SQLite remains the default, demo, CI reference, compatibility, and rollback backend.
## Consequences
Every shared contract must continue passing on SQLite. PostgreSQL cannot redefine public semantics.
## Tradeoffs
Two physical dialects and implementations require parity governance.
## Future implications
Spark, lake, and orchestration work must preserve SQLite fixtures even when production paths use PostgreSQL; Kubernetes deployment remains optional for local use.
