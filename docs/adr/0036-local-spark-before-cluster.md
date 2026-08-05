# ADR 0036: Local Spark mode before cluster deployment
## Context
Execution parity should be separated from cluster operations.
## Problem
A cluster adds networking, submission, security, and resource-management variables.
## Alternatives considered
Cluster first, managed Spark, or deterministic `local[*]` mode.
## Decision
Default Spark master is local mode with controlled timezone and shuffle partitions.
## Consequences
Developers can verify semantics on one machine.
## Tradeoffs
Local timing does not establish cluster-scale performance.
## Future implications
Cluster master configuration can change without modifying transformation policy.
