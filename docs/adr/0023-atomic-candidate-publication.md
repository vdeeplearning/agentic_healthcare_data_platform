# ADR 0023: Atomic candidate publication
## Context
Readers must never observe half-written or failed outputs.
## Problem
Writing directly to active paths can replace good data before validation completes.
## Alternatives considered
Direct overwrite, database-only transactions, directory swapping, and candidate plus active-pointer publication were considered.
## Decision
Write objects through staging, register a candidate manifest, validate, then atomically replace the active snapshot pointer.
## Consequences
Failed candidates retain diagnostics and the prior active snapshot remains selected.
## Tradeoffs
Metadata and object cleanup require lifecycle management.
## Future migration implications
Cloud adapters will use immutable prefixes plus conditional pointer updates.
