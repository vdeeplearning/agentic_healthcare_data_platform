# Interview talking points

## 30-second explanation

I built a synthetic healthcare analytics platform where a model can interpret a question and propose SQL, but deterministic code owns authorization. It validates privacy, schema, SQL structure, complexity, metrics, execution, and evidence grounding. I then extended the same contracts through a medallion lake, Python/Spark parity, Airflow coordination, Kubernetes manifests, audit, lineage, tests, and CI.

## Two-minute explanation

Start with the risk: plausible text-to-SQL is not the same as safe or correct analytics. Explain the typed plan, AST validator, read-only backend, result checks, and audit. Then explain contract-first evolution: storage-independent records, datasets/manifests/snapshots, raw/bronze/silver/gold, canonical Python, optional Spark parity, thin Airflow orchestration, and deployment-only Kubernetes. Close with verification honesty: Python/SQLite/API/UI ran locally; PostgreSQL, real Spark, native Airflow, and live Kubernetes are implemented but await their external runtimes.

## Likely questions and truthful answers

**Why is Python canonical?** It provides deterministic, dependency-light semantics that Spark must match before scale is introduced.

**Why not let the model repair or approve SQL?** Generation and self-review share probabilistic failure modes. Deterministic authorization remains independent.

**What failed during development?** CI exposed a non-portable `tests` namespace import; explicit package-relative imports fixed it. Docker and live cluster verification were also unavailable, so those claims were narrowed rather than fabricated.

**What tradeoff did local storage make?** It maximizes transparency and reproducibility but constrains concurrency and multi-node scaling.

**What would you productionize next?** Identity, external secrets, encrypted replicated storage, live PostgreSQL/Spark/Airflow/Kubernetes gates, observability, backups, and incident runbooks—without changing analytical contracts.

**What did you learn?** Introduce boundaries before infrastructure, keep policy separate from execution, and encode verification status as carefully as feature status.

## Evolution

Bounded analyst → storage-neutral records → durable manifests/snapshots → PostgreSQL boundary → local medallion lake → Spark parity → Airflow orchestration → Kubernetes packaging → recruiter-friendly verified demo.

