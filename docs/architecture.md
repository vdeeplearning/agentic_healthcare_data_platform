# Architecture

The system divides probabilistic interpretation from deterministic authority. A typed plan must precede SQL. The SQLGlot validator owns permission to query; the model never owns a database handle. SQLite is opened in URI `mode=ro` with `query_only=ON`, a progress handler enforces time, and results are capped. The current credential-free implementation uses curated planners; the live-model extension point must emit the same `AnalysisPlan` and SQL candidate contracts.

The graph is bounded: clarification and denial terminate immediately; SQL has at most two repair opportunities by design (the baseline performs zero automatic repairs); result repair is limited to one; answer validation permits one evidence-only rewrite. Trace events expose decisions, not hidden reasoning.

## Platform seams

The workflow now depends on narrow `QueryBackend`, `AuditStore`, and `Planner` contracts. SQLite implementations preserve the original behavior and remain the only enabled implementations. Catalog metadata and query results use engine-neutral internal models, while deterministic SQL authorization, privacy controls, metric governance, result checks, statistics, and answer grounding remain centralized. See [distributed platform foundation](platform_foundation.md) and the [architecture decisions](adr/).

Synthetic construction follows a separate path: the versioned logical generator emits typed entity batches; `SyntheticDatasetLoader` implementations own schema creation, transactional persistence, validation, and manifests. The current `SQLiteSyntheticDatasetLoader` is the only loader. Dataset identity is derived from generation inputs, while load timestamps and backend details belong to the manifest. Relationship metadata is characterized in [relationship policy](relationship_policy.md) but remains intentionally unenforced.

