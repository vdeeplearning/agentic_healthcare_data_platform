# ADR 0035: Central quality policy independent of Spark
## Context
Quality gates authorize publication.
## Problem
Duplicated thresholds in Spark could diverge from Python.
## Alternatives considered
Spark-specific checks, SQL checks, or shared deterministic policy evaluation.
## Decision
Both engines use the same `quality_checks` policy and metric registry.
## Consequences
Spark executes checks but cannot redefine them.
## Tradeoffs
Some normalized validation evidence returns to the driver in local mode.
## Future implications
Distributed check implementations must reproduce identical structured results.
