# ADR 0016: Add PostgreSQL as an optional serving backend

- Status: Accepted
- Date: 2026-08-05

## Context
The abstractions need proof against a second engine with production-style transactions, roles, timeouts, and catalogs.
## Problem
SQLite alone cannot demonstrate that query, loader, snapshot, and safety boundaries are truly engine-neutral.
## Alternatives considered
- Keep abstract interfaces unproven.
- Add a distributed engine first: too large and mixes concerns.
- Add PostgreSQL now: focused proof of serving portability.
## Decision
Implement psycopg 3 `PostgresQueryBackend` and `PostgresLoader`, selected only through configuration.
## Consequences
Applications may opt into PostgreSQL without route or response changes. SQLite remains default.
## Tradeoffs
PostgreSQL requires a running service, DSN, schema ownership, and operational maintenance.
## Future implications
Gold data can later publish into PostgreSQL; Spark remains deterministic batch transformation, Airflow scheduling, and Kubernetes deployment—not query authorization.
