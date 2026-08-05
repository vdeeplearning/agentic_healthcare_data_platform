# ADR 0012: Use explicit lightweight metadata migrations

- Status: Accepted
- Date: 2026-08-05

## Context
Durable metadata schemas evolve independently from healthcare analytical tables.

## Problem
Ad hoc `CREATE IF NOT EXISTS` statements cannot prove upgrade order, rollback, or future-version compatibility.

## Alternatives considered
- Alembic now: capable but adds machinery and an unnecessary dependency.
- Recreate metadata on startup: destroys lineage.
- Ordered transactional SQLite migrations: sufficient for the current boundary.

## Decision
Record numbered migrations in `platform_metadata_migrations`, run each in `BEGIN IMMEDIATE`, roll back failed versions, make repeats safe, and reject unknown future versions.

## Consequences
Fresh, repeated, prior-version, failed, and future-version cases are testable. Healthcare DDL remains untouched except for the additive audit provenance column.

## Tradeoffs
SQL is maintained in Python migration definitions and currently targets SQLite only.

## Future implications
The same numbered intent will map to reviewed PostgreSQL migrations later; Airflow may check versions but not apply application startup migrations; Spark/lake schemas remain separately versioned; Kubernetes rollout ordering must respect migration compatibility.

