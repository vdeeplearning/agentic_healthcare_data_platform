# ADR 0040: Defer Kubernetes until after Airflow
## Context
Kubernetes is the final operational target.
## Problem
Deploying before scheduler, external state, readiness, and service boundaries mature creates YAML without operational proof.
## Alternatives considered
Kubernetes now, Spark-on-Kubernetes now, or phased deployment after Airflow.
## Decision
Keep Kubernetes deferred.
## Consequences
No cluster manifests or operators are added in this milestone.
## Tradeoffs
Only local Spark mode is currently supported by the repository workflow.
## Future implications
Kubernetes follows independently deployable services, externalized state, readiness, and tested Airflow behavior.
