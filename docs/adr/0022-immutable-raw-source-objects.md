# ADR 0022: Immutable raw source objects
## Context
Source evidence must remain reproducible even when malformed.
## Problem
Overwriting received data destroys the ability to explain later cleaning decisions.
## Alternatives considered
Mutable landing files, database staging tables, and content-addressed immutable objects were considered.
## Decision
Raw object identifiers are immutable; identical rewrites are idempotent and conflicting content is rejected.
## Consequences
Malformed lines remain available while downstream gates may reject them.
## Tradeoffs
Retention grows and correction requires a new source batch.
## Future migration implications
Object storage must use retention/versioning and conditional creation.
