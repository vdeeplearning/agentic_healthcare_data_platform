# ADR 0001: Preserve SQLite as the compatibility backend

- Status: Accepted
- Date: 2026-08-05

## Decision

SQLite remains the default, permanent local/demo backend and the canonical compatibility fixture. New serving backends will be opt-in implementations of the query and audit contracts. They must pass common contract, safety, semantic, and provenance tests before activation.

## Consequences

Existing users retain credential-free startup, deterministic seeding, Docker Compose behavior, and a straightforward rollback path. Backend-neutral models may not erase SQLite-specific safety guarantees; adapters must provide equivalent or stronger controls.

