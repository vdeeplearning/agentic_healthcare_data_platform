# ADR 0046: Kubernetes is a deployment and operations layer only
## Context
The analytical, lake, Spark, Airflow, serving, audit, and lineage contracts are stable.
## Problem
Adding a cluster scheduler could accidentally create alternate transformation, policy, or metadata behavior.
## Alternatives considered
Embed Kubernetes-aware business logic, introduce Kubernetes-specific pipelines, or deploy the existing components unchanged.
## Decision
Kubernetes manifests package and operate existing commands, configuration, probes, storage mounts, and network endpoints only. They do not define SQL, metrics, quality gates, privacy, lineage, or transformations.
## Consequences
The API and analytical behavior remain identical across local, Compose, and Kubernetes execution.
## Tradeoffs
Kubernetes cannot compensate for application-level limitations such as local SQLite concurrency or local-filesystem atomicity.
## Future implications
Any new operator or controller must invoke the same reviewed application contracts.

