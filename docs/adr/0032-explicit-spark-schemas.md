# ADR 0032: Explicit Spark schemas
## Context
Inference can vary with nulls, input size, and Spark version.
## Problem
Inferred identifiers, flags, dates, and numerics can drift and break parity.
## Alternatives considered
Inference, per-job schemas, or one explicit project schema registry.
## Decision
Define every entity field and physical metadata column explicitly.
## Consequences
Type intent and nullability are reviewable and tested.
## Tradeoffs
Schema evolution requires deliberate code changes.
## Future implications
Parquet and cluster implementations reuse these schemas and compatibility checks.
