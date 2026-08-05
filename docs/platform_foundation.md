# Distributed platform foundation

This milestone adds internal contracts without changing the application's public behavior. SQLite remains the only enabled backend, the default for every entry point, and the permanent local compatibility and rollback implementation.

## Frozen compatibility surface

Compatibility tests protect the FastAPI OpenAPI fingerprint; request and response models; status values; trace ordering; configuration defaults and `CLINICAL_SQL_` environment names; curated questions and grounded answers; metric definitions; privacy denial and small-cell suppression; audit serialization; SQLite tables, views, indexes, and deterministic seed invariants; Streamlit behavior; and benchmark cases. Run IDs, timestamps, and measured latency are normalized or excluded from strict comparisons.

## Internal boundaries

`QueryBackend` discovers an engine-neutral catalog and executes SQL that has already been approved by the central validator. It cannot approve SQL. `SQLiteQueryBackend` retains URI read-only connections, `query_only`, cooperative timeout, `EXPLAIN QUERY PLAN`, row limits, normalized rows, and provenance.

`AuditStore` separates provenance persistence from analytical execution even though both currently use the same SQLite file. `SQLiteAuditStore` preserves the current `/runs` row shape and treats a repeated run ID idempotently without overwriting its original event.

`Planner` adapts both deterministic curated lookup and OpenAI Structured Outputs. A planner receives no database connection or execution capability. The OpenAI adapter continues to receive bounded schema metadata and approved conversation context through the existing generator.

The `Analyst` constructor remains backward compatible. Optional keyword-only dependencies support contract testing and future implementations. Privacy classification, SQL policy, result validation, small-cell suppression, metric governance, statistical tools, and answer grounding remain centralized and backend-independent.

The relationship allowlist remains catalog metadata only. The legacy validator did not enforce it, so enabling it is deliberately deferred to a separately tested safety-hardening change rather than being hidden inside this refactor.

## Future data lifecycle

- **Raw:** immutable source exports plus source and batch identity.
- **Bronze:** minimally transformed ingested records with batch, ingestion, and source metadata.
- **Silver:** typed, cleaned, deduplicated, conformed, and deterministically validated records.
- **Gold:** analytics-ready tables and governed materializations of registered metrics.

The current generator now has fixture-profile, dataset-identity, and loader seams. It still writes only SQLite. Later loaders may emit raw files, Parquet, Spark DataFrames, or PostgreSQL records without changing deterministic domain generation.

PySpark will eventually implement reviewed, versioned transformations and data-quality rules. Models will not generate or execute arbitrary Spark code. PostgreSQL will later be an opt-in serving adapter using a SELECT-only role and server-side statement timeout; SQLite remains available for parity and rollback.

Airflow will schedule ingestion, Spark transformations, data-quality checks, gold publication, benchmarks, and failure handling. It will not execute the latency-sensitive interactive `/analyze` workflow. Kubernetes is deliberately last, after service boundaries, readiness checks, idempotency, state externalization, observability, and resource requirements are demonstrated.

## Provenance direction

Future provenance will connect source object and batch IDs to transformation version and Spark job, Airflow DAG run, gold dataset version, serving-database snapshot, validated SQL, approved statistics, and the final audited answer. The new execution context and result provenance fields provide internal homes for dataset and snapshot identity without altering today's public response.

