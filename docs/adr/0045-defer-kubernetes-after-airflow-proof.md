# ADR 0045: Defer Kubernetes after Airflow proof
## Context
Airflow now coordinates local state and local serving publication.
## Problem
Kubernetes deployment would require external state, image boundaries, secrets, readiness, and recovery behavior.
## Alternatives considered
Add Helm now, use KubernetesExecutor, or defer cluster deployment.
## Decision
Do not add Kubernetes, Helm, Terraform, or cloud services in this milestone.
## Consequences
The repository proves scheduling semantics without pretending local files are multi-pod storage.
## Tradeoffs
Airflow and Spark remain local developer workflows.
## Future implications
The next milestone must first externalize state and define independently deployable services before Kubernetes work begins.
