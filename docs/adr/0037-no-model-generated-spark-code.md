# ADR 0037: No arbitrary model-generated Spark code
## Context
The platform invariant gives deterministic software execution authority.
## Problem
Executing model-generated Spark expressions would bypass review, privacy, and quality controls.
## Alternatives considered
Free-form notebooks, constrained expression generation, or reviewed fixed transformations only.
## Decision
The LLM cannot author or execute Spark transformations; named reviewed functions are the only jobs.
## Consequences
Spark remains outside interactive `/analyze` and cannot approve SQL or metrics.
## Tradeoffs
New transformations require normal engineering review and release.
## Future implications
Airflow may schedule only registered implementations, never model-provided code.
