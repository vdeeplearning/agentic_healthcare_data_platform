# Exact demo narration

## 0:00–0:20 — problem

“This is an agentic healthcare analytics platform built entirely on synthetic data. Ordinary text-to-SQL demos can produce plausible queries and execute them immediately. Here, the model can propose an analysis, but deterministic software decides what is safe, valid, bounded, and supported by evidence.”

## 0:20–0:50 — architecture

“A question becomes a typed plan and one SQL candidate. Privacy policy and an AST-based validator inspect the request, schema, joins, functions, complexity, and limits. Only approved SQL reaches a read-only serving backend. The returned rows are checked again before the system writes a grounded answer and audit record.”

## 0:50–1:20 — lake and Spark

“Behind the analyst is a versioned medallion pipeline. Raw preserves source evidence, bronze adds ingestion metadata, silver types and validates records, and gold prepares analytical tables. Deterministic Python is canonical. An optional PySpark engine implements the same contracts, with parity based on normalized logical results—not unstable partition filenames.”

## 1:20–1:45 — orchestration

“Airflow coordinates these existing stages: source, transforms, quality gates, publication, and verification. It records run metadata and stops on failure, but contains no transformation or policy logic. A failed candidate never replaces the active validated snapshot.”

## 1:45–2:45 — analysis

“I’ll choose a deterministic question about encounter volume. The result is not just a chat response. We can inspect the typed population and grouping plan, the generated SQL, and the validation report. Execution is read-only and bounded. The chart and answer are built from the verified rows, so numeric claims have an inspectable source.”

## 2:45–3:30 — safeguards

“The trace shows each authorization and verification step. If I request patient-level identifiers, the privacy classifier denies the request before SQL execution. Small cohorts are suppressed, unsafe statements are rejected structurally, and statistical analysis is limited to fixed registered tools. The model cannot override any of those controls.”

## 3:30–4:15 — audit and lineage

“Every run has an audit ID. From this answer, lineage resolves the serving snapshot, gold, silver, bronze, raw snapshot, and source batch. Airflow and Spark runtime identifiers can be added to that chain, while Kubernetes remains only the deployment layer.”

## 4:15–4:45 — breadth and truthfulness

“The platform includes SQLite and an optional PostgreSQL backend, canonical Python and optional PySpark, Airflow orchestration, Kubernetes manifests, Docker Compose, CI, and extensive tests. This matrix is intentionally precise: local Python and SQLite ran here; external PostgreSQL, Java and Spark, native Airflow, and a live Kubernetes cluster remain environment-dependent.”

## 4:45–5:00 — close

“The central engineering principle is simple: the model proposes; deterministic software authorizes and verifies. The repository includes a one-command demo, architecture decisions, tests, release notes, and the full verification boundary.”

## Caption text

Use the narration verbatim as captions, with line breaks at sentence boundaries. Always retain the phrases “synthetic data,” “optional,” and “environment-dependent” where spoken.

