# ADR 0043: SequentialExecutor or LocalExecutor before distributed workers
## Context
The milestone targets one local filesystem and explicitly excludes Kubernetes and Celery.
## Problem
A distributed executor would imply shared remote state and operational services that do not exist yet.
## Alternatives considered
SequentialExecutor, LocalExecutor, CeleryExecutor, and KubernetesExecutor were considered.
## Decision
Support SequentialExecutor for simplest development and LocalExecutor for controlled parallel local tasks.
## Consequences
No broker, Celery worker, Helm chart, or cluster is required.
## Tradeoffs
Local filesystem state prevents safe multi-host execution.
## Future implications
External storage and independently deployable services must precede any distributed executor.
