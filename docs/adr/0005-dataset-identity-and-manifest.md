# ADR 0005: Version dataset identity and manifests

- Status: Accepted
- Date: 2026-08-05

## Context

A seed alone does not identify a dataset when fixture size, formulas, or schema can change.

## Problem

Audits and future batch jobs need a stable name for equivalent logical data and a record of when and how that data was loaded.

## Alternatives considered

- Use the seed as identity. Insufficient when parameters change.
- Hash every serialized row. Strong but expensive for routine generation.
- Hash generation inputs and store stable summaries. Efficient and explicit.

## Decision

Derive `dataset_id` from seed, fixture profile, generator version, schema version, and major parameters using canonical JSON and SHA-256. Keep timestamps and load results in a separate manifest so they do not make identity nondeterministic.

## Consequences

Equivalent inputs have the same identity; changed inputs have a different identity. The returned manifest records entity counts, loader, timestamps, validation, and stable aggregate summaries without changing the legacy seed command output.

## Tradeoffs

Input-derived identity assumes the version is incremented whenever formulas change. It is not a cryptographic checksum of every row.

## Future implications

Manifests can later be persisted beside raw batches and referenced by database snapshots, DAG runs, and audits.

