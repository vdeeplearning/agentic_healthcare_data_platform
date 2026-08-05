# ADR 0010: Distinguish dataset, manifest, and snapshot identity

- Status: Accepted
- Date: 2026-08-05

## Context
One logical dataset may be loaded repeatedly or materialized into several technologies.

## Problem
Using one identifier for both logical facts and physical materializations cannot distinguish SQLite, future PostgreSQL, or gold Parquet copies.

## Alternatives considered
- Use dataset ID everywhere: simple but ambiguous.
- Use random snapshot IDs: distinct but not reproducible.
- Hash stable identity inputs at each layer: deterministic and explainable.

## Decision
Dataset identity hashes generation inputs. Manifest identity hashes stable logical contents and summaries. Snapshot identity hashes dataset/manifest IDs, backend, schemas, loader/version, storage identity, and materialization parameters. Timestamps never affect these hashes.

## Consequences
Equivalent materializations resolve idempotently while backend, loader, or materialization changes produce a new snapshot ID.

## Tradeoffs
Version discipline is required; identities are input-derived rather than full row-content hashes.

## Future implications
Spark outputs, lake gold tables, and PostgreSQL serving copies can share a dataset ID while retaining distinct snapshot IDs and Airflow load-event timestamps.

