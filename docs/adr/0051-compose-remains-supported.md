# ADR 0051: Keep Docker Compose supported
## Context
Compose is the simplest way to run the API, UI, and optional PostgreSQL stack on one workstation.
## Problem
Replacing Compose with Kubernetes would raise the local-development barrier and make a cluster mandatory.
## Alternatives considered
Kubernetes-only development, Compose-only deployment, and parallel supported paths were considered.
## Decision
Keep existing Dockerfiles and Compose files supported. Kubernetes adds an operations option; it does not supersede local Python or Compose workflows.
## Consequences
Contributors can choose the smallest environment appropriate to their task.
## Tradeoffs
Container commands and environment mappings must remain consistent across two deployment descriptions.
## Future implications
CI validation must continue checking Compose and Kubernetes configuration independently.

