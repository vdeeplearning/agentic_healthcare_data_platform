# ADR 0029: Defer Airflow and Kubernetes
## Context
Scheduling and deployment should orchestrate stable components rather than define their semantics.
## Problem
Premature DAGs and manifests create operational surface without mature jobs and service boundaries.
## Alternatives considered
Airflow DAGs now, Kubernetes Compose replacement, cron, and explicit local CLI commands were considered.
## Decision
Keep explicit CLI stages and defer Airflow and Kubernetes.
## Consequences
Developers can inspect every step; scheduling, retries, secrets, and multi-service operations remain manual.
## Tradeoffs
There is no production scheduler or cluster deployment in this milestone.
## Future migration implications
Airflow will call existing transformations after Spark integration; Kubernetes remains the final deployment milestone.
