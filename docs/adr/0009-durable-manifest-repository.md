# ADR 0009: Use a durable, separate manifest repository

- Status: Accepted
- Date: 2026-08-05

## Context
Manifests previously existed only in a returned Python object. They disappeared when the process ended.

## Problem
Audits and future batch systems need stable lookup of logical datasets and materializations without giving query execution metadata-write authority.

## Alternatives considered
- Put metadata in application memory: simple but not durable.
- Put tables in the analytical catalog: durable but exposes platform internals to SQL discovery and reseeding.
- Use a SQLite sidecar behind a narrow store: durable, local, and separately authorized.

## Decision
Use `ManifestStore` and `SQLiteManifestStore` with an adjacent metadata database. Registration is idempotent for identical stable content and rejects conflicting identifier reuse.

## Consequences
Local startup stays credential-free and analytical schema behavior stays unchanged. Metadata survives replacement of the analytics database.

## Tradeoffs
Two SQLite files must be backed up together. The sidecar is not yet a multi-process production metadata service.

## Future implications
PostgreSQL can implement the same store; Spark and Airflow can register manifests and snapshots; lake objects can reference IDs; Kubernetes only deploys these components and does not define lineage semantics.

