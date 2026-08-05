# ADR 0041: Airflow is an optional orchestrator
## Context
The project has established Python and Spark transformation contracts but no scheduler.
## Problem
Scheduling must not make Airflow mandatory for the local analyst or redefine transformations.
## Alternatives considered
Cron, an in-process scheduler, mandatory Airflow, and optional Airflow were considered.
## Decision
Add Airflow as an optional dependency and discovery DAG around a runtime-independent `PipelineOrchestrator`.
## Consequences
The default project remains lightweight; Airflow environments gain manual, scheduled, and backfill execution.
## Tradeoffs
Real DAG import tests skip when Airflow is absent.
## Future implications
External executors may be added later only if they preserve the same stage and metadata contracts.
