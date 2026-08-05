# ADR 0018: Run one reusable contract suite against both engines

- Status: Accepted
- Date: 2026-08-05

## Context
The SQLite contract mixin already defines backend obligations.
## Problem
Duplicated PostgreSQL tests could quietly check different guarantees.
## Alternatives considered
- Separate hand-written suites: flexible but prone to drift.
- Mock-only PostgreSQL tests: fast but cannot prove server behavior.
- Shared contracts plus unit and opt-in integration layers: balanced.
## Decision
SQLite always runs the shared suite. PostgreSQL runs the identical suite when `CLINICAL_SQL_TEST_POSTGRES_DSN` is configured, supplemented by driver-free orchestration tests and snapshot/result parity integration.
## Consequences
CI can add a PostgreSQL service without changing test definitions; local zero-service runs remain viable and clearly report skips.
## Tradeoffs
An environment without PostgreSQL cannot claim live parity execution.
## Future implications
Future backend implementations inherit the same suite; Airflow or Kubernetes are not prerequisites for contract testing.
