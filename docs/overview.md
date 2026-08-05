# Platform overview

## Problem

Ordinary text-to-SQL demos can generate plausible SQL and execute it immediately. In healthcare analytics that pattern can expose sensitive detail, use the wrong cohort, calculate an unregistered metric, or present unsupported numbers confidently.

## Approach

This platform separates proposal from authority. Language-oriented code interprets a question and proposes a typed plan. Deterministic software owns privacy classification, SQL authorization, schema access, registered metrics, statistical tools, execution limits, result validation, grounding, audit, and lineage.

The data path is equally explicit: versioned synthetic sources move through raw, bronze, silver, and gold snapshots before publication to SQLite or optional PostgreSQL. Python is canonical; PySpark implements the same reviewed contracts. Airflow coordinates those contracts. Kubernetes deploys their containers and commands.

## Boundaries

- The model cannot approve SQL, run arbitrary Python, submit Spark expressions, change metrics, or lower privacy thresholds.
- Airflow contains no transformations or policy.
- Kubernetes contains no analytical logic.
- SQLite remains the default path requiring the fewest external services.
- All included healthcare data is synthetic.

Return to the [README](../README.md) or continue to [architecture](architecture.md).

