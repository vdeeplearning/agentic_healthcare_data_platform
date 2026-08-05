# ADR 0002: Separate deterministic SQL policy from execution

- Status: Accepted
- Date: 2026-08-05

## Decision

The central SQL validator exclusively authorizes queries. `QueryBackend` implementations only discover metadata, inspect plans, execute already validated read-only SQL, enforce resource controls, normalize results, and report provenance.

Privacy suppression, metric definitions, result validation, statistical tools, and answer grounding also remain outside execution adapters. The existing relationship allowlist is recorded but will not be newly enforced during this compatibility refactor.

## Consequences

PostgreSQL or distributed execution cannot bypass deterministic authority. Dialect capabilities can vary without relocating policy into infrastructure code.

