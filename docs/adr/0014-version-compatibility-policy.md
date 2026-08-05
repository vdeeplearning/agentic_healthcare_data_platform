# ADR 0014: Enforce a small major-version compatibility policy

- Status: Accepted
- Date: 2026-08-05

## Context
Generator, logical schema, loader, manifest, snapshot, analytics schema, metrics, and views evolve for different reasons.

## Problem
Treating every change equally causes unnecessary regeneration; accepting every combination risks incorrect materialization.

## Alternatives considered
- Exact-version equality: safe but overly restrictive.
- Full enterprise schema registry: premature.
- Current-major compatibility plus explicit consequences: small and reviewable.

## Decision
Accept supported major versions. Generator or logical-schema major changes require regeneration; logical-schema changes also require rematerialization; loader-major changes require rematerialization; compatible loader implementation changes may request rematerialization. Metadata migration versions remain exact and ordered.

## Consequences
Registration rejects unsupported combinations with clear decisions. Metric-definition changes remain governed separately because they may not require data regeneration.

## Tradeoffs
Minor-version semantic discipline is a human responsibility. The policy intentionally covers current needs rather than arbitrary dependency graphs.

## Future implications
PostgreSQL loaders, Spark transformations, Airflow DAGs, and lake layers must declare compatible versions; Kubernetes deploys only combinations admitted by application policy.

