# ADR 0003: Defer distributed infrastructure until contracts are proven

- Status: Accepted
- Date: 2026-08-05

## Decision

Do not add PostgreSQL, a data lake, PySpark, Airflow, or Kubernetes in this milestone. First characterize public behavior, establish query/audit/planner and dataset lifecycle seams, and prove them with SQLite contract tests.

## Consequences

PySpark will later run deterministic reviewed transformations; Airflow will orchestrate batch work rather than interactive analysis; Kubernetes will follow only after deployable service boundaries and operational requirements exist. No infrastructure dependency or paid service is required today.

