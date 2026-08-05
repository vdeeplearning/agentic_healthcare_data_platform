# ADR 0044: Airflow run metadata joins platform lineage
## Context
Analysis already resolves through serving and lake snapshots to source objects.
## Problem
Without an orchestration identifier, the scheduled execution that produced those snapshots is invisible.
## Alternatives considered
Rely only on Airflow's metadata database, copy full task logs, or store a bounded platform record.
## Decision
Persist a bounded `OrchestrationRun` keyed by DAG and Airflow run ID, and propagate its ID through lake and serving metadata.
## Consequences
Lineage can resolve analysis to Airflow run without exposing Airflow internals or filesystem paths through the API.
## Tradeoffs
Airflow's operational database and platform lineage store remain separate systems with linked IDs.
## Future implications
Production metadata may move to PostgreSQL while retaining the same model.
