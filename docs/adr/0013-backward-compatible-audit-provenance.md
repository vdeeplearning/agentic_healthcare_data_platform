# ADR 0013: Add snapshot provenance to audits compatibly

- Status: Accepted
- Date: 2026-08-05

## Context
Audit rows already preserve question, plan, SQL, validation, results, statistics, warnings, and answer, but not a durable snapshot reference.

## Problem
Changing existing columns would break `/runs`, old databases, and portfolio compatibility.

## Alternatives considered
- Replace the audit schema: breaking.
- Put IDs only in answer provenance: not durable enough.
- Add one optional JSON field and migrate old tables: additive and flexible.

## Decision
Add nullable `provenance_json`. Deterministic platform code supplies dataset, manifest, snapshot, backend, schema, and loader IDs. Old rows deserialize with `NULL`; legacy analyses without metadata still work.

## Consequences
Run lineage resolves through `LineageResolver` without trusting the model or changing response models and trace ordering.

## Tradeoffs
JSON is less query-friendly than normalized audit foreign keys, but avoids coupling audit persistence to one metadata implementation.

## Future implications
PostgreSQL can use JSONB or normalized references; Airflow and Spark identifiers can be added compatibly; lake lineage can extend the payload; Kubernetes has no authority to generate provenance values.

