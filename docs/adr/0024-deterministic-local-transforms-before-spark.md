# ADR 0024: Deterministic local transforms before Spark
## Context
Transformation semantics should be testable independently of distributed execution.
## Problem
Introducing Spark now would conflate business rules with cluster behavior.
## Alternatives considered
PySpark first, pandas, SQL scripts, and reviewed ordinary Python were considered.
## Decision
Implement versioned deterministic Python transforms with no model-generated code execution.
## Consequences
Small fixtures prove behavior without Java or a cluster.
## Tradeoffs
The implementation is not intended for large production volumes.
## Future migration implications
PySpark will implement the same inputs, outputs, identities, and quality gates.
