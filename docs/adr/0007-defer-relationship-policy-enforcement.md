# ADR 0007: Characterize but defer relationship-policy enforcement

- Status: Accepted
- Date: 2026-08-05

## Context

The catalog lists approved foreign-key-like relationships. The existing validator requires a nontrivial join predicate but does not require predicates to match that list.

## Problem

Silently enabling enforcement would newly reject syntactically valid queries and could break curated, live, or user-validated SQL without a focused safety review.

## Alternatives considered

- Enable strict enforcement during this refactor. Stronger immediately, but a breaking behavior change.
- Remove relationship metadata. Loses the intended policy direction.
- Freeze current behavior and characterize the future delta. Safest migration path.

## Decision

Keep enforcement disabled. Tests prove Cartesian joins are rejected while non-Cartesian unregistered joins remain accepted. Maintain an explicit fixture of queries expected to become newly rejected.

## Consequences

Current behavior is preserved and the gap is visible rather than implied. Relationship validation needs its own design, compatibility analysis, and release note.

## Tradeoffs

Until that milestone, a semantically inappropriate equality join may pass structural validation.

## Future implications

The proposed policy should resolve aliases, composite keys, views, CTE lineage, self-joins, and approved derived relationships before enforcement.

