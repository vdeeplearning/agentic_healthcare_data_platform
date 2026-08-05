# ADR 0011: Activate snapshots only after validated replacement

- Status: Accepted
- Date: 2026-08-05

## Context
The seed command historically rebuilt its target in place. A failed rebuild could remove the last usable database.

## Problem
Metadata must never claim an invalid load is active, and a failed attempt must not displace the last validated snapshot.

## Alternatives considered
- Delete and rebuild in place: simplest but unsafe.
- Activate metadata before load: creates false lineage on failure.
- Stage, validate, replace, then transactionally activate: failure-safe with modest local complexity.

## Decision
Load a staging database, validate it, register an inactive snapshot, atomically replace the target, and then activate metadata. Preserve and restore the previous file if activation fails. Failed validation records an inactive failed snapshot.

## Consequences
The prior active snapshot and physical database survive failed generation, loading, validation, or activation.

## Tradeoffs
Temporary disk space is required during replacement. Filesystem replacement and metadata activation cannot form one cross-file ACID transaction, so backup restoration bridges that boundary.

## Future implications
PostgreSQL may use transactional schema swaps; gold publication may use atomic object pointers; Airflow retries stay idempotent; Kubernetes does not replace this application-level rule.

