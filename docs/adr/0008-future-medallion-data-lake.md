# ADR 0008: Use a future raw/bronze/silver/gold lake architecture

- Status: Proposed
- Date: 2026-08-05

## Context

Large-scale ingestion needs replayable source history, deterministic cleanup, governed analytical outputs, and traceable publication.

## Problem

Loading source files directly into serving tables loses intermediate evidence and makes correction or replay difficult.

## Alternatives considered

- Direct source-to-PostgreSQL loads. Simple, but weak replay and lineage.
- Raw/curated only. Fewer layers, but combines ingestion fidelity with cleansing.
- Raw/bronze/silver/gold. More storage and governance, but explicit responsibilities.

## Decision

When a lake is authorized, use immutable raw exports; bronze ingested records with batch metadata; silver typed, deduplicated, validated records; and gold analytics-ready tables and governed metric materializations.

## Consequences

Each transition can be tested, replayed, and linked to a manifest. Serving databases consume gold outputs rather than arbitrary raw files.

## Tradeoffs

The extra layers require retention policy, schema evolution, quality gates, and operational ownership.

## Future implications

PySpark will run reviewed deterministic transformations. Airflow will schedule batch transitions. Neither will authorize interactive AI-generated execution; Kubernetes remains a later deployment decision.

