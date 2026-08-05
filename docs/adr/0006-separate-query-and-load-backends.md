# ADR 0006: Separate query backends from dataset loaders

- Status: Accepted
- Date: 2026-08-05

## Context

Interactive analytics reads governed data, while dataset publication creates schemas and writes batches.

## Problem

A single interface with both powers would give interactive code unnecessary mutation authority and make safety review ambiguous.

## Alternatives considered

- One database adapter for all operations. Convenient but violates least privilege.
- Repository objects per table. Excessive abstraction for bulk synthetic fixtures.
- Narrow query and loader protocols. Clear authority and small surface area.

## Decision

Keep `QueryBackend` read-only and separately define `SyntheticDatasetLoader` for schema creation, transactional batches, validation, and manifests. SQLite has one implementation of each; they do not call one another.

## Consequences

The analyst cannot gain load permissions through its query dependency. Future production deployments can use separate credentials and processes.

## Tradeoffs

Some metadata concepts appear in both boundaries and must remain version-compatible.

## Future implications

PostgreSQL query and load adapters, plus lake writers, can evolve independently and receive purpose-specific permissions.

