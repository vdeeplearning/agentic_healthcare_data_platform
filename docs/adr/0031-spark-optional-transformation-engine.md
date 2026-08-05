# ADR 0031: Spark is an optional transformation implementation
## Context
The lake contracts need a scalable execution option without changing users' default setup.
## Problem
A mandatory PySpark dependency would impose Java and a large install on every contributor.
## Alternatives considered
Mandatory Spark, a separate repository, or an optional dependency and engine boundary.
## Decision
Provide `PySparkTransformationEngine` through the `spark` optional dependency group; Python remains default.
## Consequences
Spark capability is explicit and lazy-loaded.
## Tradeoffs
Some integration tests skip when Java or PySpark is unavailable.
## Future implications
Cluster submission can later implement the same engine protocol.
