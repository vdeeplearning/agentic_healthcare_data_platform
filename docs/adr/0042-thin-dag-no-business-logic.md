# ADR 0042: DAG tasks contain no business logic
## Context
Python and Spark engines, quality policy, serving loaders, and verification are authoritative.
## Problem
Embedding transformations or thresholds in DAG files would create a competing policy implementation.
## Alternatives considered
SQL-heavy DAGs, custom transformation operators, or thin Python callables were considered.
## Decision
Every Airflow task calls one named `PipelineOrchestrator` stage and exchanges identifiers through XCom.
## Consequences
Task ordering is visible while business behavior stays testable without Airflow.
## Tradeoffs
Workers must import the project package and access the configured local state.
## Future implications
Airflow may later submit Spark jobs, but it must still call registered engine contracts.
