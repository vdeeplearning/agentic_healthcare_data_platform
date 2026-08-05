# Agentic Clinical SQL Analyst

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)](#testing) [![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)](#quick-start) [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A portfolio-grade, constrained analytics agent that turns natural-language questions into typed analysis plans, validated read-only SQL, verified statistics, and evidence-grounded answers over an entirely synthetic healthcare database. It demonstrates relational design, practical SQL, agentic orchestration, FastAPI, Streamlit, statistical tooling, Docker, CI, auditability, and explainability—without requiring a paid service to launch.

> **Synthetic data only. Educational/portfolio software, not a clinical decision system.** No record represents a real patient, provider, or hospital.

## Screenshots

| Analysis workspace | Validation and audit |
|---|---|
| ![Analysis workspace showing a natural-language question and verified hospital encounter results](docs/screenshots/analysis.png) | ![Validation and audit trace showing successful bounded workflow steps](docs/screenshots/audit.png) |

## Why this exists

Text-to-SQL demos often give a model excessive authority and trust plausible-looking output. This project separates interpretation from authority. The agent can propose a registered metric and SQL candidate, but deterministic code decides whether the query may run, recomputes important quantities, suppresses small cells, and checks whether the answer is supported.

### Key features

- 12-table normalized SQLite model, foreign keys, checks, indexes, views, and reproducible synthetic data
- Credential-free deterministic agent supporting curated analytical questions against the real database
- Pydantic analysis plans before SQL; ambiguity such as “Which hospital is worst?” triggers clarification
- SQLGlot single-statement AST checks, table/column/function allowlists, join/resource controls, and row limits
- SQLite URI read-only mode, `query_only`, timeout progress handler, and `EXPLAIN QUERY PLAN`
- Registered healthcare metrics and fixed statistical tools; arbitrary generated Python never runs
- Result plausibility checks, deterministic arithmetic, small-cell suppression, grounded answer templates
- FastAPI/OpenAPI, polished Streamlit UI, JSON audit trail, benchmarks, pytest, Docker Compose, and CI
- 20 annotated reference queries covering joins, CTEs, subqueries, date logic, views, indexes, and windows

## What the safety-focused description means in plain English

The project description says that it uses a **bounded AI workflow with structured planning, SQLGlot validation, privacy controls, approved statistical tools, deterministic result checks, evidence-grounded answers, and complete audit trails**. Put simply, the AI is allowed to suggest an analysis, but it is not trusted with unrestricted control. Ordinary application code decides what is safe to run, checks the results, limits what may be shown, and records what happened.

### Bounded AI workflow

“Bounded” means the AI operates inside a fixed process with clear limits. It can interpret a question and propose how to answer it, but it cannot connect directly to the database, change the database, run arbitrary programs, or retry forever.

For example, the workflow follows steps such as:

1. Understand the user's question.
2. Decide whether the question is clear and safe.
3. Create a structured analysis plan.
4. Propose SQL.
5. Validate the SQL with ordinary code.
6. Inspect the database query plan.
7. Execute the query through a read-only connection.
8. Check and suppress the returned results where necessary.
9. Optionally run one approved statistical function.
10. Produce an answer based only on verified evidence.
11. Save an audit record.

If the question is unclear—such as “Which hospital is worst?”—the application asks what “worst” means. If a request is unsafe, such as asking for patient-level exports, it is denied. If validation fails, execution stops safely.

### Structured planning

The AI cannot jump directly from a user's question to database execution. It must first complete a structured analysis plan that identifies items such as:

- the metric being requested;
- the population or cohort to analyze;
- inclusion and exclusion rules;
- the date range;
- grouping and comparison fields;
- the required database tables;
- the minimum acceptable group size;
- whether a statistical test is needed; and
- whether the question is ambiguous or presents a privacy risk.

Pydantic checks that this plan has the required fields and valid data types. This is similar to requiring someone to complete a standardized request form before they are allowed to submit a database query.

### SQLGlot validation

SQLGlot turns proposed SQL into a structured syntax tree so the application can inspect what the query actually does. This is safer than searching the SQL text for suspicious words because the validator can identify the statement type, tables, columns, functions, and joins.

The validator rejects, among other things:

- attempts to insert, update, or delete data;
- attempts to create, alter, replace, or drop database objects;
- multiple SQL statements hidden in one request;
- access to SQLite system tables or administrative commands;
- tables or columns that do not exist in the approved schema;
- functions that are not on the allowlist;
- joins without meaningful matching conditions; and
- queries that exceed configured complexity or result-size limits.

Even SQL that passes these checks is executed through a separate read-only database connection. The SQL validator and database permissions therefore provide two independent layers of protection.

### Privacy controls

The application is designed to return summarized information rather than individual records. Although the included data is synthetic, the project models privacy practices that would matter when working with healthcare information.

- Aggregate counts, rates, and trends are the default.
- Patient-level output and unrestricted exports are denied.
- Requests involving sensitive demographic combinations are flagged.
- Groups with fewer than 10 observations are suppressed.
- Only a small, verified result sample is provided as context for follow-up questions.
- API keys and direct identifiers are not written to audit logs.

For example, the application may report a hospital's complication rate when enough eligible cases exist, but it will not provide a list of the patients behind that rate.

### Approved statistical tools

The AI cannot write and execute arbitrary Python. It may only select a statistical operation from a predefined registry of reviewed functions, including:

- proportion confidence intervals;
- chi-square tests;
- Fisher exact tests;
- independent-samples t-tests;
- Mann–Whitney U tests;
- one-way ANOVA; and
- Pearson or Spearman correlations.

These functions check their inputs, sample sizes, missing values, and assumptions before running. They return structured results and warnings. The AI chooses from the available tools, but the application—not the AI—owns and executes the underlying Python implementation.

### Deterministic result checks

“Deterministic” means the same input is checked using explicit programming rules rather than model judgment. After a SQL query runs, ordinary Python code verifies conditions such as:

- denominators must be positive;
- counts cannot be negative;
- a numerator cannot exceed its denominator;
- rates must remain between 0 and 1;
- percentages must remain between 0 and 100;
- empty results must be reported clearly;
- suspicious values should produce warnings; and
- small groups must remain suppressed.

Important arithmetic is calculated from verified database values. The application does not ask the language model to perform or guess the final calculations.

### Evidence-grounded answers

The final answer is limited to information found in the validated plan, executed SQL, verified result table, approved statistical output, and recorded warnings. Names, categories, sample sizes, percentages, rankings, and comparisons must come from that evidence.

If the query returns no evidence—or if the evidence does not support a conclusion—the application should say so. It should not fill gaps with plausible-sounding medical or operational claims.

### Complete audit trails

Every analysis receives a unique run ID. The audit record stores information needed to reconstruct how the answer was produced, including:

- the original and normalized question;
- the selected model and schema version;
- the structured analysis plan;
- the generated and validated SQL;
- validation and execution status;
- execution time and returned row count;
- approved statistical tools used;
- warnings and limitations;
- the final grounded answer; and
- the creation timestamp.

Secrets such as OpenAI API keys are deliberately excluded. The audit trail makes the system easier to debug, test, explain, and review without exposing credentials.

### The division of responsibility

| The AI may | Deterministic application code must |
|---|---|
| Interpret the user's wording | Classify privacy risk and enforce policy |
| Identify ambiguity | Validate the structured plan |
| Select a registered metric | Control the metric definitions |
| Propose one SQL query | Parse, allowlist, limit, and approve the SQL |
| Request an approved statistical tool | Validate inputs and execute the fixed function |
| Draft an interpretation | Check values and ground claims in verified evidence |

The central idea is straightforward: **the AI proposes; deterministic software verifies and controls**.

## Architecture

```mermaid
flowchart LR
 U["User and Streamlit interface"]
 API["FastAPI service"]
 G["Bounded agent workflow"]
 P["Pydantic analysis plan"]
 V["SQLGlot and policy validators"]
 Q["Query-plan review and read-only SQLite"]
 R["Result and privacy validators"]
 S["Approved statistical tools"]
 A["Grounded answer validator"]
 L["Audit log"]

 U --> API
 API --> G
 G --> P
 P --> V
 V --> Q
 Q --> R
 R --> S
 S --> A
 G --> L
```

```mermaid
flowchart TD
 N["Normalize question"]
 C{"Classify risk and intent"}
 CL["Ask for clarification and stop"]
 D["Deny unsafe request and stop"]
 P["Create typed analysis plan"]
 PV["Validate analysis plan"]
 QG["Generate SQL candidate"]
 SV["Validate AST, schema, and joins"]
 EP["Inspect query plan"]
 EX["Execute through read-only connection"]
 RV["Validate and suppress results"]
 ST["Run optional approved statistic"]
 GA["Compose grounded answer"]
 FV["Check answer faithfulness"]
 AU["Write audit record"]

 N --> C
 C -- "Ambiguous" --> CL
 C -- "High risk" --> D
 C -- "Safe and clear" --> P
 P --> PV
 PV --> QG
 QG --> SV
 SV --> EP
 EP --> EX
 EX --> RV
 RV --> ST
 ST --> GA
 GA --> FV
 FV --> AU
```

```mermaid
erDiagram
 PATIENTS ||--o{ ENCOUNTERS : has
 HOSPITALS ||--o{ PROVIDERS : employs
 HOSPITALS ||--o{ ENCOUNTERS : hosts
 PROVIDERS ||--o{ ENCOUNTERS : attends
 ENCOUNTERS ||--o{ ENCOUNTER_DIAGNOSES : coded
 DIAGNOSES ||--o{ ENCOUNTER_DIAGNOSES : classifies
 ENCOUNTERS ||--o{ ENCOUNTER_PROCEDURES : receives
 PROCEDURES ||--o{ ENCOUNTER_PROCEDURES : defines
 ENCOUNTERS ||--o{ LAB_RESULTS : produces
 ENCOUNTERS ||--o| READMISSIONS : index
 HOSPITALS ||--o{ QUALITY_MEASURES : reports
```

Safeguards stack from outside inward: **privacy classification → typed plan → metric registry → AST/schema/join allowlists → plan inspection/resource caps → read-only database → result checks/suppression → fixed statistics → answer faithfulness → immutable provenance record**.

## Database and SQL

`patients`, `hospitals`, `providers`, and `encounters` form the core. Diagnoses and procedures use normalized vocabularies with many-to-many bridge tables. Labs, readmissions, quarterly quality measures, and audits are separate facts. The seeded full profile creates approximately 25,000 patients, 30 hospitals, 200 providers, and 100,000 encounters. Hospital risk, diagnosis, age proxy, rurality, seasonality, and temporal trends generate useful analytical variation. Controlled missingness, suspicious dates, rare categories, inconsistent codes, and small cohorts support quality tests.

The [reference curriculum](sql/reference_queries/README.md) visibly demonstrates `SELECT`, filtering, sorting, grouping, `HAVING`, inner/left joins, CTEs, subqueries, `CASE`, dates, aggregates, `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `LAG`, rolling windows, views, parameterization, indexes, and `EXPLAIN QUERY PLAN`. Database construction uses an explicit transaction.

## What is agentic—and what is not

The workflow observes state, selects a bounded path, can request clarification, chooses a registered metric/tool, and records structured actions. It is not fully autonomous: retry limits are finite (two SQL repairs, one result repair, one evidence-only answer rewrite as extension contracts), high-risk requests terminate, and deterministic components retain execution authority. The trace shows decisions, validators, tool calls, warnings, and retry reasons—not hidden chain-of-thought.

The LLM does **not** directly execute unrestricted SQL. Generated SQL is parsed before execution; the database handle is read-only. The model cannot redefine metrics, calculate final rates, run arbitrary Python, expose small groups, or add claims absent from verified evidence. Model self-critique is secondary because a model can confidently repeat its own mistake.

The baseline demo is intentionally deterministic. When a session-only API key is supplied, non-demo questions use the OpenAI Responses API with Pydantic Structured Outputs to propose an `AnalysisPlan` and one SQL candidate. That candidate passes through exactly the same non-bypassable deterministic pipeline; OpenAI never receives a database connection and the API key is never logged. Curated questions remain deterministic for reproducible demonstrations.

## Metrics, privacy, statistics, and provenance

The registry fixes numerator, denominator, eligibility, sample size, unit, grouping, null handling, and caveats for readmission, mortality, complications, length of stay, emergency conversion, cost, volume, and prevalence. Rates are checked and important ratios are computed from numerator/denominator output.

Aggregate results are the default. Direct identifiers and patient-level exports are high risk and denied. Sensitive demographic combinations are medium risk, explicitly warned, and groups under 10 are suppressed. Only the minimum result fields needed for an answer should reach a live model.

Approved tools include Wilson proportion intervals, chi-square, Fisher exact, Welch t-test, Mann–Whitney U, one-way ANOVA, and Pearson/Spearman correlations. Each validates types/sample size and returns structured estimates, effects, assumptions, and warnings. Regression and standardization are documented extension points in this MVP.

Every run receives an ID and records question, normalized intent, model label, schema version, plan, SQL, validation/execution status, timing, row count, statistical tool, warnings, answer, and timestamp. API keys are excluded.

## Example

Question: “Which hospitals had the highest 30-day readmission rates for heart failure in 2025?”

```sql
WITH cohort AS (... validated eligibility joins ...)
SELECT hospital_name, COUNT(*) AS denominator,
       SUM(readmitted_within_30_days) AS numerator,
       1.0 * SUM(readmitted_within_30_days) / COUNT(*) AS readmission_rate
FROM cohort JOIN hospitals USING (hospital_id)
GROUP BY hospital_id, hospital_name
HAVING COUNT(*) >= 10
ORDER BY readmission_rate DESC;
```

Output includes the direct answer, verified table/chart, sample size, fixed metric definition, caveats, exact validated SQL, referenced tables/columns, optional test result, trace, query-plan provenance, and audit ID. If evidence is empty or inconclusive, the answer says so.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m src.database.seed --patients 2500 --encounters 10000
uvicorn src.api.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs). In another terminal:

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). No key is required. For the full dataset, run `python -m src.database.seed` (100,000 encounters). Configuration lives in [.env.example](.env.example); never commit `.env`.

### Testing and benchmark

```bash
python -m pytest
python -m src.cli benchmark
```

The seed benchmark spans aggregation, joins, rates, cohorts, ambiguity, privacy denial, statistics, and prompt injection. It reports executable SQL rate, exact table selection, clarification/denial accuracy, and latency. See [evaluation design](docs/evaluation.md). Benchmark results are intentionally a placeholder until run in CI against a pinned release artifact.

### Docker

```bash
docker compose up --build
```

API: port 8000; UI: port 8501; generated data uses a named volume.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/`, `/health` | metadata and readiness |
| GET | `/schema`, `/metrics` | allowlisted schema and registry |
| POST | `/analyze` | execute the bounded workflow |
| POST | `/validate-sql` | validate without execution |
| GET | `/runs`, `/runs/{run_id}` | audit provenance |
| GET | `/reference-queries` | curriculum discovery |
| POST | `/demo/reset` | safely refuses destructive HTTP reset |

Full contracts are in OpenAPI and [docs/api.md](docs/api.md).

## Project map

`src/agent` owns typed orchestration and planner adapters; `src/safety` deterministic policy; `src/database` engine-neutral catalog/execution contracts, the SQLite backend, and synthetic-data lifecycle seams; `src/metrics` immutable definitions; `src/statistics` fixed tools; `src/audit` the audit-store contract and SQLite provenance; `src/api` FastAPI; `src/ui` Streamlit; `src/evaluation` benchmarks; `sql` schema/views/indexes/reference queries; `tests` regression and compatibility coverage; `docs` design detail and ADRs. See the [distributed platform foundation](docs/platform_foundation.md).

## Versioned data generation and backend contracts

This milestone changes the inside of dataset construction while deliberately leaving the outside of the application alone. The same seed command still creates the same SQLite fixture, returns the same summary dictionary, and supports the same API, UI, CLI, curated questions, safeguards, and audits. Internally, generation now emits typed logical records in bounded batches, and a separate SQLite loader persists them. A reusable contract suite defines what every future analytical query backend must prove.

```mermaid
flowchart LR
 I["Seed, fixture profile, generator version, parameters"]
 G["Deterministic logical record generator"]
 B["Typed record batches"]
 L["SQLite dataset loader"]
 DB["SQLite compatibility database"]
 M["Versioned dataset manifest"]
 Q["Read-only QueryBackend"]
 A["Bounded analyst workflow"]

 I --> G --> B --> L --> DB
 I --> M
 L --> M
 DB --> Q --> A
```

### Logical domain records

A logical domain record represents one healthcare concept without saying where it will be stored. `PatientRecord`, for example, has a patient ID, fictional birth date, sex, race/ethnicity, insurance, region, and creation timestamp. It is not a SQLite row object, PostgreSQL command, JSON document, Parquet object, or Spark row. It is a typed description of the synthetic fact that any reviewed writer can consume.

The project has typed records for patients, hospitals, providers, encounters, diagnosis and procedure vocabularies, encounter links, labs, readmissions, and quality measures. The generator yields batches instead of constructing the full 100,000-encounter fixture as one giant list. It retains only the small lookup state needed to preserve the established formulas and build readmissions deterministically.

#### What this means in plain English

Imagine writing a shipping label before deciding whether the package will travel by truck, train, or plane. The address is the same fact regardless of transport. Logical records are the address; SQLite is currently the truck. Later, a PostgreSQL loader or lake writer can carry the same records without inventing a different dataset.

#### What would happen without this layer?

Every storage technology would grow its own copy of the synthetic formulas. A small difference in random-number ordering, null handling, rounding, or eligibility logic could produce different hospital rates for the same seed. Tests would no longer know whether a discrepancy came from storage or from data generation.

### Deterministic, versioned generation

`SyntheticRecordGenerator` owns the existing probability distributions, correlations, controlled missingness, and deliberate quality anomalies. `GENERATOR_VERSION` identifies that formula set. The seed and major parameters still control NumPy's random generator in the same order, so existing row counts and known aggregate results remain stable.

```mermaid
flowchart TD
 S["Seed and generation parameters"] --> H["Hospitals and providers"]
 H --> P["Patient batches"]
 P --> V["Diagnosis and procedure vocabularies"]
 V --> E["Encounter plus link and lab batches"]
 E --> R["Readmission batches"]
 R --> QM["Quarterly quality-measure batches"]
 QM --> O["Any approved loader or writer"]
```

#### What this means in plain English

The seed is a repeatable starting point, while the generator version says which recipe was used. Seed `17` with recipe `1.0.0` and the same fixture size produces the same logical records. If the recipe changes, the version must change even if the seed does not.

#### What would happen without this layer?

A seed by itself would create false confidence. Code changes could alter the dataset while logs continued to say only “seed 17,” making benchmark drift and audit reconstruction difficult to explain.

### Dataset identity

A dataset ID is a deterministic SHA-256-derived identifier computed from canonical generation inputs:

- random seed;
- fixture profile;
- generator version;
- schema version; and
- major parameters such as patient and encounter counts.

Timestamps and backend names are deliberately excluded. Loading the same logical dataset tomorrow or loading it into another approved store should not change its logical identity.

```python
dataset_identity(17, "test").dataset_id
# synthetic-clinical-<stable digest>

dataset_identity(18, "test").dataset_id
# different digest because the seed changed

dataset_identity(17, "test", encounters=1201).dataset_id
# different digest because a major parameter changed
```

#### What this means in plain English

Dataset identity is a reproducible name for the recipe inputs, similar to a fingerprint on a sealed batch. It answers “Are these meant to be the same logical data?” before comparing millions of rows.

#### What would happen without this layer?

Two databases named `clinical.db` could contain different fixtures but appear interchangeable. Conversely, identical logical data loaded at different times could be mistaken for unrelated datasets.

### Dataset manifest

The manifest records both logical identity and the outcome of a specific load. `generate_dataset(...)` exposes it without changing the historical `generate_database(...)` or CLI output.

```json
{
  "dataset_id": "synthetic-clinical-<stable digest>",
  "generator_version": "1.0.0",
  "schema_version": "1.0",
  "fixture_profile": "test",
  "random_seed": 17,
  "generation_parameters": {"patients": 300, "encounters": 1200, "hospitals": 30, "providers": 200},
  "entity_row_counts": {"patients": 300, "encounters": 1200, "hospitals": 30},
  "loader_backend": "sqlite",
  "load_complete": true,
  "validation_summary": {"foreign_key_errors": 0, "quality_measure_errors": 0},
  "source_type": "synthetic",
  "clinical_use_disclaimer": "Synthetic data only; not for clinical decisions or patient care."
}
```

The actual manifest also contains generation/load timestamps, counts for every emitted entity, and stable summaries such as total encounter cost. Timestamps describe a load event but do not affect dataset identity.

#### What this means in plain English

If dataset identity is the batch number, the manifest is the packing slip. It states what was expected, what was loaded, which loader handled it, whether validation passed, and when the work occurred.

#### What would happen without this layer?

A successful process exit would be the only evidence of a good load. Operators could not readily distinguish a complete fixture from one missing labs, links, or quality measures.

### QueryBackend contract

`QueryBackend` is the narrow read-only boundary used by interactive analysis. Its reusable test suite checks catalog normalization, tables and views, prohibited objects, capabilities, read-only enforcement, normalized rows and nulls, numeric types, query plans, execution timing, row truncation, timeout behavior, structured failures, and provenance.

The contract does not allow a backend to approve SQL. Central SQL policy still parses the candidate, rejects unsafe statements, checks schema and complexity, and inserts a row limit before execution. A future PostgreSQL adapter must pass the same shared tests plus its own engine-specific tests.

#### What this means in plain English

A backend is a replaceable database driver with a strict job description. It can describe approved data and run a query that has already received permission. It cannot give itself permission.

#### What would happen without this layer?

Adding PostgreSQL would require database-specific branches throughout the analyst. Safety behavior could accidentally depend on which database was selected, and parity would be tested inconsistently.

### Query execution and dataset loading are separate

The query backend can only read. `SyntheticDatasetLoader` has a different responsibility: create a schema, load typed batches in a transaction, build indexes and views, validate the completed dataset, and return a manifest. The interactive `Analyst` receives the query interface, never the loader.

```mermaid
flowchart LR
 GR["Logical record batches"] --> WL["Write-authorized dataset loader"] --> DS["Governed dataset"]
 SQL["Centrally validated SQL"] --> QR["Read-only query backend"] --> DS
 DS --> RES["Normalized query result"]
```

#### What this means in plain English

The employee who stocks a locked archive and the employee who reads approved files have different keys. The analyst gets the reading key. Batch publication gets the stocking key only while loading.

#### What would happen without this layer?

Interactive code would carry write powers it does not need. A future credential or adapter mistake could turn a read-only analytical request into a data mutation path.

### Invariants and compatibility

Invariant tests verify row counts, foreign keys, uniqueness, categorical domains, date rules, numerator/denominator relationships, valid rates, same-seed equivalence, changed-parameter identity changes, and curated-query answers. Backend contract tests are reusable: a future implementation supplies backend and catalog fixtures and inherits the same behavioral checks.

The generator intentionally retains the established rare suspicious discharge-date pattern for quality demonstrations. Small fixtures that do not reach the anomaly interval require ordinary date ordering; larger profiles characterize the deliberate exceptions instead of silently “fixing” them.

#### What this means in plain English

An invariant is a fact that must remain true even while the plumbing changes. We do not merely check that generation finishes; we check that the result still tells the same analytical story and obeys the same integrity rules.

#### What would happen without this layer?

A refactor could produce the right number of rows but attach diagnoses to the wrong encounters, change a rate, lose a null, or alter a curated ranking without an obvious crash.

### Relationship policy remains deliberately disabled

The catalog describes approved join relationships, but the current validator only requires a meaningful join predicate. Tests explicitly show that Cartesian joins are rejected while an unregistered equality join remains accepted. [Relationship-policy characterization](docs/relationship_policy.md) lists the metadata and the intended future contract.

#### What this means in plain English

The application currently checks that two tables are connected with a real condition, but it does not yet prove that the condition is the medically and relationally intended key. That stronger rule is visible on the roadmap, not quietly enabled inside an unrelated refactor.

#### What would happen without this layer?

Silently enabling the list could break existing SQL. Silently ignoring the gap would overstate current safeguards. Characterization tests make both the present behavior and the future change reviewable.

### How this prepares the distributed platform

```mermaid
flowchart LR
 SRC["Synthetic or future source batch"] --> RAW["Raw: immutable source"]
 RAW --> BR["Bronze: ingested plus batch metadata"]
 BR --> SI["Silver: typed, cleaned, deduplicated, validated"]
 SI --> GO["Gold: analytics-ready governed metrics"]
 GO --> PG["Future PostgreSQL serving"]
 GO --> SQ["SQLite compatibility fixture"]
 PG --> QA["Validated interactive analysis"]
 SQ --> QA
```

PostgreSQL will later add production-style serving, using separate SELECT-only and loading credentials. The same logical batches can also be serialized as raw JSON/CSV, Parquet, or Spark DataFrames. Raw preserves the immutable source; bronze adds ingestion metadata; silver applies deterministic typing, cleanup, deduplication, and validation; gold exposes reviewed analytical tables and registered metric materializations.

PySpark will run reviewed transformation code over versioned records. It will not execute arbitrary model-generated Python or Spark expressions. Airflow will schedule ingestion, transformations, quality gates, publication, and benchmarks; it will not handle latency-sensitive `/analyze` requests. Kubernetes remains last because deployment orchestration is useful only after service boundaries, state, health checks, idempotency, resource requirements, and operational ownership are established.

#### What this means in plain English

The project is preparing standardized boxes, labels, and inspection rules before buying a larger warehouse and delivery fleet. PostgreSQL, Spark, Airflow, and Kubernetes will later fill specific roles; none should redefine the data or weaken permission checks.

#### What would happen without this layer?

Infrastructure would arrive before its responsibilities were clear. The result would be more moving parts, duplicated rules, difficult debugging, and no reliable proof that a final answer came from the intended source batch.

### End-to-end provenance direction

The intended lineage is:

```text
source batch
  → versioned logical records
  → loader and load manifest
  → database or gold snapshot
  → centrally validated SQL
  → verified rows and approved statistics
  → evidence-grounded answer and audit record
```

Execution context already has internal dataset, snapshot, fixture-profile, and generator-version fields. The current public response remains unchanged. Later milestones can persist manifest references and snapshot identity in audit storage through an additive, versioned migration.

#### What this means in plain English

Provenance is the chain of receipts behind an answer. A reviewer should eventually be able to move backward from a sentence in the UI to the query, database snapshot, load event, transformation version, and original source batch.

#### What would happen without this layer?

An answer might be numerically plausible but impossible to reproduce after data refreshes or code changes.

### Tradeoffs and current limitations

- SQLite is still the only implementation; portability is proven by contracts and logical inputs, not yet by a second engine.
- Dataset identity hashes generation inputs and relies on disciplined generator-version changes; it does not hash every row.
- Manifests are returned programmatically but are not yet written to an external registry or audit table.
- The generator streams large fact batches but retains compact primary-diagnosis and inpatient eligibility state for readmission generation.
- Backend errors are structured internally; the public API retains its existing safe failure response.
- Relationship metadata remains descriptive until a separately reviewed enforcement milestone.
- The synthetic anomaly schedule remains part of compatibility and must not be interpreted as valid clinical data.

### Beginner-friendly setup and verification

No paid service or infrastructure platform is required:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"

# Small local fixture through the unchanged command
python -m src.database.seed --patients 300 --encounters 1200 --seed 17

# Regression and reusable backend contracts
python -m pytest

# Coverage and deterministic benchmark
python -m pytest --cov=src --cov-report=term-missing
python -m src.cli benchmark --limit 5
```

To inspect a manifest without changing the CLI contract:

```python
from pathlib import Path
from src.database.seed import generate_dataset

result = generate_dataset(Path("data/generated/clinical.db"), seed=17, patients=300, encounters=1200)
print(result.manifest.model_dump_json(indent=2))
```

The generated database remains synthetic and must never be replaced with PHI.

## Durable manifests, snapshots, and answer lineage

The previous foundation could calculate a manifest but held it only in a Python return value. This milestone makes logical manifests and concrete snapshots durable in a separate SQLite metadata repository. It also attaches an optional snapshot reference to new audit rows. Nothing about the question-to-answer contract changed: API models, routes, UI behavior, trace ordering, SQL safeguards, privacy suppression, metrics, statistics, curated answers, and the historical seed-command output remain compatible.

```mermaid
flowchart LR
 G["Versioned generation inputs"] --> R["Logical record batches"]
 R --> M["Logical dataset manifest"]
 M --> L["Validated SQLite load"]
 L --> S["Concrete SQLite snapshot"]
 S --> A["Active snapshot pointer"]
```

### Dataset, manifest, snapshot, and load event

A **dataset** is the logical collection of generated healthcare facts. A **manifest** is the durable description of those logical facts: generator and schema versions, seed, fixture profile, parameters, entity counts, stable summaries, source type, and disclaimer. A **snapshot** is one concrete materialization of that manifest in a particular backend with a particular loader and schema. A **load event** is the time-dependent attempt that created or failed to create a snapshot.

The same logical test dataset can be loaded twice into the same SQLite target. Its dataset and manifest IDs remain stable, and the equivalent materialization resolves idempotently. The same dataset loaded into future PostgreSQL has the same dataset and manifest IDs but a different snapshot ID because the backend changed.

#### What this means in plain English

The dataset is a book's text. The manifest is the title and edition record. A snapshot is one printed copy—hardcover, paperback, or e-book. The print date describes a production event, but it does not rewrite the book's identity.

#### What would happen without this layer?

“The dataset” would ambiguously mean formulas, rows, a file, or a database server. An audit could point to `clinical.db` without proving which generation recipe or load produced it.

### Why a loaded database is a snapshot

SQLite contains one current materialization of logical records. Calling the file “the dataset” hides that another valid copy could exist in a restored SQLite file, future PostgreSQL, or a gold Parquet table. Snapshot metadata records loader/backend identity, schema, storage identity, materialization parameters, row counts, validation results, load status, supersession, and optional source batches.

```mermaid
flowchart TD
 D["One logical dataset ID"] --> SS["SQLite snapshot"]
 D --> PS["Future PostgreSQL serving snapshot"]
 D --> GS["Future gold Parquet snapshot"]
 SS --> SID1["Snapshot ID A"]
 PS --> SID2["Snapshot ID B"]
 GS --> SID3["Snapshot ID C"]
```

#### What this means in plain English

One photograph can have copies on a laptop, phone, and archive drive. They depict the same image but are different stored copies with different formats and operational histories.

#### What would happen without this layer?

A future PostgreSQL refresh could overwrite the only known identity, making it impossible to distinguish the database queried yesterday from the database queried today.

### Stable identity and volatile timestamps

Dataset identity hashes seed, fixture profile, generator version, logical schema version, and major generation parameters. Manifest identity additionally describes stable logical output summaries. Snapshot identity hashes dataset and manifest IDs, backend, loader/version, analytics schema, storage identity, snapshot schema, and materialization parameters.

Generation and load timestamps do **not** participate in stable hashes. Repeating the same load an hour later should not invent a new logical identity merely because the clock changed. Timestamp differences remain recorded as load-event metadata.

```text
same seed + profile + generator + parameters
    = same dataset ID

same dataset + manifest + backend + loader + materialization settings
    = same snapshot ID

change SQLite → PostgreSQL or loader 1.x → 2.x
    = different snapshot ID
```

#### What this means in plain English

A recipe is not a different recipe each time someone cooks it. The cooking time belongs on the kitchen log; ingredients and instructions define the recipe.

#### What would happen without this layer?

Retries would create endless identities for equivalent outputs, idempotency would be impossible, and Airflow or Spark reruns could not distinguish “same work repeated” from “different data produced.”

### The manifest repository

`ManifestStore` is separate from `QueryBackend`, `AuditStore`, generation, and loading. `SQLiteManifestStore` currently writes an adjacent `*.metadata.db` sidecar. It stores no API keys and avoids full local paths; storage identity is a bounded logical filename. Stable ordering makes listings reproducible.

Registration rules are strict:

- an identical manifest or snapshot registration returns the existing record;
- reuse of an identifier with conflicting stable content raises `MetadataConflictError`;
- a snapshot must reference a registered matching manifest;
- incompatible versions are rejected;
- unknown metadata migration versions are rejected rather than guessed.

#### What this means in plain English

The repository is a library catalog. Adding the same catalog card twice is harmless. Reusing the same catalog number for a different book is an error, not an update.

#### What would happen without this layer?

Lineage would disappear on process restart, or conflicting metadata could silently rewrite history after an answer had already been audited.

### Failure-safe snapshot activation

The SQLite loader no longer destroys the active target before knowing a replacement is valid. It creates a uniquely named staging database, loads batches transactionally, builds indexes and views, validates foreign keys and quality measures, registers an inactive snapshot, replaces the target, and only then marks the snapshot active. A backup bridges the small boundary between filesystem replacement and metadata activation.

```mermaid
flowchart TD
 O["Old active snapshot and database"] --> ST["Build staging database"]
 ST --> V{"Validation passed?"}
 V -- "No" --> F["Record inactive failure; keep old active"]
 V -- "Yes" --> RS["Register inactive validated snapshot"]
 RS --> SW["Replace database with backup available"]
 SW --> AC{"Metadata activation succeeded?"}
 AC -- "Yes" --> N["New active; old superseded"]
 AC -- "No" --> RB["Restore old database and active metadata"]
```

A failed generation registers no completed manifest. A failed validation may leave an inactive failure record, but it cannot replace the active snapshot. Partial migration or registration transactions roll back.

#### What this means in plain English

Do not throw away the working bridge until the replacement bridge has passed inspection and is ready to open. If inspection fails, traffic continues over the old bridge.

#### What would happen without this layer?

A random generation exception, disk error, or failed invariant could leave no usable demo database while metadata incorrectly advertised a bad load as current.

### Metadata schema migrations

Platform metadata has its own numbered migration history. Migration 1 creates manifests; migration 2 creates snapshots, indexes, and the one-active-snapshot constraint. Each unapplied migration runs under `BEGIN IMMEDIATE` and records its version only after success. Startup can safely apply migrations repeatedly. An unknown future version stops processing.

```mermaid
flowchart LR
 OP["Open metadata store"] --> MT["Ensure migration ledger"]
 MT --> CV["Read applied versions"]
 CV --> FV{"Unknown future version?"}
 FV -- "Yes" --> STOP["Stop safely"]
 FV -- "No" --> NX["Begin next migration"]
 NX --> SQL["Apply statements"]
 SQL --> OK{"All succeeded?"}
 OK -- "No" --> ROLLBACK["Rollback version"]
 OK -- "Yes" --> REC["Record version and commit"]
 REC --> NX
```

The healthcare schema is not being converted into a general migration framework. The current mechanism covers platform metadata; the audit table receives one additive nullable provenance column with an idempotent legacy upgrade.

#### What this means in plain English

A migration is a numbered renovation instruction. The repository remembers which renovations succeeded. If step two fails, it undoes step two instead of leaving half a wall removed.

#### What would happen without this layer?

Two installations could claim to use the same metadata schema while having different tables or columns, and a newer application could misread an older or future database.

### Backward-compatible audit provenance

New audit rows may contain `provenance_json` with deterministic `dataset_id`, `manifest_id`, `snapshot_id`, backend, analytics schema, and loader version. Existing columns are unchanged. Old audit tables are upgraded additively; old rows return `NULL` provenance and remain readable. If metadata is absent or corrupt, analysis runs in legacy-compatible mode and gains no additional query permission.

The model never supplies these identifiers. `Analyst` resolves the active snapshot from the deterministic sidecar and passes it through internal execution context.

```mermaid
flowchart RL
 ANS["Evidence-grounded answer"] --> RUN["Audit run ID"]
 RUN --> PROV["Optional provenance IDs"]
 PROV --> SNAP["Snapshot record"]
 SNAP --> MAN["Manifest record"]
 MAN --> GEN["Generator version, seed, profile, parameters"]
 SNAP --> LOAD["Loader, backend, schema, counts, validation"]
```

#### What this means in plain English

The audit now has a receipt number for the exact warehouse shipment it used. Older receipts without that number are still valid historical documents; they simply cannot provide the newer lookup.

#### What would happen without this layer?

The project could reproduce SQL but not prove which concrete database state produced the rows, especially after refreshes.

### Resolving an answer back to generation

`LineageResolver` starts with a run ID, reads its optional provenance, loads the snapshot, then loads the manifest. The result explains which snapshot was queried; the dataset and manifest IDs; generator version, seed, profile, and parameters; loader/backend/schema; row counts; and validation summary.

Example journey:

```text
run 7ca…
  → snapshot-41d… (SQLite, loader 1.0.0, active at analysis time)
  → manifest-c24…
  → synthetic-clinical-73c…
  → generator 1.0.0, seed 17, test profile, 300 patients / 1,200 encounters
```

No public endpoint was added because the internal lineage model should mature before becoming another compatibility surface. Existing `/runs` endpoints remain additive-compatible through the nullable audit field.

#### What this means in plain English

Given a statement in the UI, a reviewer can follow breadcrumbs backward to the recipe and load inspection that produced its evidence.

#### What would happen without this layer?

“We ran the same query” would not guarantee reproduction because the underlying rows might have come from another refresh.

### Version compatibility and schema evolution

The project distinguishes change types instead of treating every version bump alike. The current policy accepts supported major versions and returns whether regeneration or rematerialization is required.

- A backward-compatible optional manifest field needs neither regeneration nor rematerialization.
- A generator formula or RNG-order change needs regeneration and a generator version change.
- An incompatible logical-schema change needs regeneration and rematerialization.
- A loader-only refactor with identical output does not change dataset identity; policy may request rematerialization.
- A loader major or physical-format change needs a new snapshot.
- An index or analytical-view change affects the analytical snapshot, not logical record identity.
- A metric-definition change belongs to metric governance and may require recomputing gold outputs without regenerating source records.
- Metadata schema versions use exact numbered migrations.

See [version compatibility rules](docs/version_compatibility.md).

#### What this means in plain English

Changing the book's text, changing the printing press, adding a library index, and changing how a reviewer scores the book are four different changes. They should not all force the same work.

#### What would happen without this layer?

The system would either reject harmless upgrades or combine incompatible generators, loaders, and schemas until an analytical discrepancy appeared.

### Current SQLite architecture

```mermaid
flowchart LR
 CLI["Unchanged seed CLI"] --> LG["Logical generator"]
 LG --> SL["Write-authorized SQLite loader"]
 SL --> ADB["SQLite analytics database"]
 SL --> MS["SQLite metadata sidecar"]
 API["FastAPI / Streamlit / CLI analyst"] --> QB["Read-only SQLite QueryBackend"]
 QB --> ADB
 API --> AUD["SQLite audit store"]
 AUD --> ADB
 API -. "resolve active snapshot" .-> MS
```

The metadata sidecar is separate from the analytical query interface even when it sits beside the same local database. It is ignored by the SQL catalog and is not sent to the model.

#### What this means in plain English

There are now three sets of keys: one stocks the database, one reads approved analytical data, and one maintains catalog/lineage cards. The interactive agent only gets the reading capability.

### Preparing for PostgreSQL and the lakehouse

The boundaries now support a future PostgreSQL serving snapshot without changing dataset identity or central safety. A PostgreSQL loader would register a distinct snapshot using its backend, loader, schema, and storage identity. A SELECT-only PostgreSQL query backend would still have to pass the shared backend contract.

Future lakehouse lineage is expected to look like this:

```mermaid
flowchart LR
 RAW["Raw source batch"] --> BR["Bronze snapshot + ingestion metadata"]
 BR --> SI["Silver snapshot + quality results"]
 SI --> GO["Gold governed snapshot"]
 GO --> PG["PostgreSQL serving snapshot"]
 PG --> AG["Validated agent analysis"]
 AG --> AU["Audit run"]
 AU -. "lineage" .-> PG
 PG -. "lineage" .-> GO
 GO -. "lineage" .-> SI
 SI -. "lineage" .-> BR
 BR -. "lineage" .-> RAW
```

A future Spark job will consume a registered input snapshot and produce a new deterministic output snapshot with transformation-version metadata. It will not execute arbitrary AI-generated code. Airflow will schedule jobs and record batch/DAG-run identifiers as load-event provenance; it will not execute interactive `/analyze`. Kubernetes will eventually deploy services and jobs, but it is unrelated to the meaning of dataset identity or lineage.

#### What this means in plain English

Spark is a future factory, Airflow is the future shift scheduler, PostgreSQL is a future storefront, and Kubernetes is a future building manager. The manifest and snapshot records are the inventory ledger shared across them.

#### What would happen without this layer?

Each platform would create its own disconnected job IDs, leaving no reliable chain from a final answer back through gold, silver, bronze, and raw inputs.

### Current limitations and production hardening

- The manifest repository is a local SQLite sidecar, not a concurrent production metadata service.
- Filesystem replacement and metadata activation are coordinated with backup restoration, not one cross-file ACID transaction.
- Failed validation is represented as an inactive snapshot; a separate load-attempt/event table may later capture richer retry history.
- Manifest identity uses versioned inputs and stable summaries, not a checksum of every row.
- Lineage is internal; no new public endpoint was added.
- Audit provenance is JSON for compatibility rather than a database-enforced foreign key.
- Snapshot activation is scoped by backend and bounded storage identity.
- Key management, access control, encryption, immutable/tamper-evident metadata, retention, replication, disaster recovery, and concurrent-writer leasing remain production work.
- Relationship-policy enforcement remains deliberately disabled.

For local verification, the existing commands remain valid. The metadata sidecar is created automatically beside a generated database and is covered by `data/generated/*.db*` in `.gitignore`.

## Optional PostgreSQL analytical backend

PostgreSQL is now the second implementation of the analytical query and logical-record loading contracts. It is an addition, not a migration: SQLite remains the default backend, the zero-configuration demo, the always-on CI fixture, the compatibility reference, and the fastest rollback option.

Set the execution backend without changing application code:

```env
DATABASE_BACKEND=sqlite
```

or:

```env
DATABASE_BACKEND=postgres
POSTGRES_DSN=postgresql://user:password@host:5432/clinical
CLINICAL_SQL_POSTGRES_SCHEMA=public
CLINICAL_SQL_POSTGRES_STORAGE_IDENTITY=postgres:public
CLINICAL_SQL_METADATA_PATH=data/generated/postgres.metadata.db
```

Routes, request and response models, Streamlit, planner contracts, metric definitions, privacy controls, statistical tools, trace ordering, and audit behavior remain the same. Only bounded catalog discovery and execution move behind `PostgresQueryBackend`.

```mermaid
flowchart TD
 U["FastAPI, Streamlit, and CLI"] --> W["Bounded Analyst workflow"]
 W --> V["Central SQL and privacy authorization"]
 V --> F{"Configured QueryBackend"}
 F -->|"default"| SQ["Read-only SQLite backend"]
 F -->|"optional"| PG["Read-only PostgreSQL backend"]
 SQ --> NR["Normalized QueryExecutionResult"]
 PG --> NR
 NR --> RV["Shared result validation, suppression, statistics, and grounding"]
```

### What changed in this release

- Added psycopg 3 as the sole new runtime dependency.
- Added configuration-driven backend selection.
- Added PostgreSQL catalog normalization, JSON `EXPLAIN`, server-side statement timeout, read-only transactions, row limits, result normalization, and bounded provenance.
- Added logically equivalent PostgreSQL tables, constraints, foreign keys, indexes, and views.
- Added a transactional PostgreSQL loader consuming the existing logical batches.
- Reused manifest and snapshot registration; PostgreSQL materializations receive distinct snapshot IDs.
- Made SQLGlot render validated SQL in the configured dialect.
- Made live planning receive the selected backend's bounded catalog and dialect, never its DSN or connection.
- Added the identical reusable contract suite for PostgreSQL plus cross-engine snapshot and analytical parity tests.
- Added an optional Compose overlay; the original Compose file and behavior are unchanged.

#### What this means in plain English

The application learned to speak to a second database through the socket it already had. The buttons, questions, safety officer, calculations, and receipts did not change; only the database adapter behind them can be switched.

### Why PostgreSQL?

SQLite is excellent for an inspectable portfolio demo but is one local file with cooperative timeouts and limited concurrent-service operations. PostgreSQL provides server-enforced transactions, native dates, mature concurrent access, schemas, roles, server-side statement timeouts, detailed plans, and operational tooling. It is a useful production-style serving database and a focused proof that the internal contracts are real.

PostgreSQL was intentionally chosen before Spark. A second SQL serving engine tests the existing query and loader seams without simultaneously adding distributed transformation, orchestration, object storage, and deployment concerns.

#### What this means in plain English

SQLite is a reliable workshop notebook. PostgreSQL is a staffed records room designed for many controlled users. Both can hold the same governed facts, but they solve different operational problems.

### Why SQLite remains

PostgreSQL does not replace the qualities that make SQLite valuable:

- no service installation or credentials;
- deterministic databases created by one command;
- very fast local tests;
- easy inspection and copying;
- stable CI reference behavior;
- a fallback if PostgreSQL is unavailable;
- a permanent semantic compatibility fixture.

Every future backend must match SQLite's externally visible semantics; SQLite does not become a neglected “legacy mode.”

#### What this means in plain English

Adding a delivery truck does not require throwing away the bicycle that remains perfect for short local trips.

### SQLite versus PostgreSQL

| Concern | SQLite | PostgreSQL |
|---|---|---|
| Default | Yes | No, explicit opt-in |
| Startup | One local command | Running server and DSN |
| Query authority | Central validator plus query-only connection | Central validator plus read-only transaction |
| Timeout | Cooperative progress handler | Server-side `statement_timeout` |
| Query plan | `EXPLAIN QUERY PLAN` | `EXPLAIN (FORMAT JSON)` |
| Dates | ISO text | Native `DATE`/`TIMESTAMPTZ` |
| Auto IDs | SQLite row ID behavior | Identity column |
| Numeric output | Python int/float | Decimal/native values normalized to int/float |
| Loading | Staged file replacement | Transactional schema materialization |
| Best role | Demo, CI, compatibility, rollback | Production-style analytical serving |

Physical differences are expected. Logical entities, eligibility, keys, constraints, views, registered metrics, and returned analytical evidence must remain equivalent.

### One logical dataset, two snapshots

Both loaders consume `SyntheticRecordGenerator.batches()`. No PostgreSQL-specific random formula exists. Consequently, matching generator inputs create one dataset ID and one manifest ID, while backend-specific materialization creates two snapshot IDs.

```mermaid
flowchart LR
 IN["Seed 17, test profile, generator 1.0.0"] --> LR["Shared logical records"]
 LR --> M["One dataset and manifest identity"]
 M --> SL["SQLite loader"]
 M --> PL["PostgresLoader"]
 SL --> SS["SQLite snapshot ID"]
 PL --> PS["PostgreSQL snapshot ID"]
 SS --> EQ["Equivalent governed analytical results"]
 PS --> EQ
```

The backend name, loader, schema, storage identity, and materialization parameters participate in snapshot identity, so SQLite and PostgreSQL snapshots cannot be confused. Their shared dataset identity proves their intended logical origin.

#### What this means in plain English

One manuscript can produce a paperback and an e-book. They carry the same text and edition record, but each copy has its own format and inventory identifier.

### How QueryBackend made this possible

The workflow does not call `sqlite3` or psycopg directly. It asks a `QueryBackend` for an approved catalog, sends SQL only after central validation, and receives `QueryExecutionResult`. Each adapter owns only engine mechanics:

- catalog queries;
- read-only transaction setup;
- native timeout configuration;
- plan inspection;
- bounded fetching;
- type and row normalization;
- backend-safe provenance.

The adapter cannot approve SQL, redefine metrics, suppress cells, select statistical tools, or ground answers. Those remain common deterministic stages after execution.

#### What this means in plain English

Both database drivers must pass through the same security checkpoint. A driver can operate its vehicle; it cannot issue itself a travel permit.

### PostgreSQL loading

`PostgresLoader` uses the same logical records as SQLite, creates the configured schema transactionally, applies the PostgreSQL physical DDL, loads batches with psycopg, checks actual row counts and quality invariants, and registers the same logical manifest plus a PostgreSQL snapshot. A failed database transaction rolls back and cannot activate a snapshot.

Run an explicit small load:

```bash
python -m src.database.postgres_loader \
  --dsn "postgresql://user:password@localhost:5432/clinical" \
  --schema public \
  --metadata-path data/generated/postgres.metadata.db \
  --storage-identity postgres:public \
  --seed 17 --patients 300 --encounters 1200
```

The existing `python -m src.database.seed` command remains SQLite-only and unchanged.

### Optional Docker Compose PostgreSQL stack

The original command still launches the original SQLite API/UI stack:

```bash
docker compose up --build
```

Use the overlay only when PostgreSQL is wanted:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

The overlay adds PostgreSQL and a one-shot logical-record loader, then configures the API for PostgreSQL. Its bundled password is explicitly local synthetic-demo configuration, not a production secret.

### Backend parity testing

`QueryBackendContract` runs unchanged against both engines. It checks catalogs, normalized types, hidden objects, centralized mutation rejection, backend read-only enforcement, nulls, numerics, plans, row growth, truncation, timeout cancellation, execution timing, identity, and provenance.

PostgreSQL integration tests are opt-in so ordinary SQLite contributors still need no server:

```bash
set CLINICAL_SQL_TEST_POSTGRES_DSN=postgresql://user:password@localhost:5432/clinical
python -m pytest tests/test_postgres_integration.py
```

Unit tests exercise driver normalization, backend orchestration, loader batching, manifests, and snapshot identity without a server. The live suite is the authority for claiming real server parity.

#### What this means in plain English

Both engines sit the same driving test. PostgreSQL also has garage tests for its own machinery. If no PostgreSQL server exists, the report says the road test was skipped rather than pretending a mock is a server.

### Performance discussion

This milestone establishes correctness boundaries, not a universal performance winner. SQLite often wins tiny local startup and fixture tests because it has no network round trip. PostgreSQL is designed for concurrent sessions, server memory management, parallel planning, role-based operations, and larger durable serving workloads.

Performance comparisons must use equivalent snapshots, warm/cold cache labels, fixed query sets, server configuration, network location, and result limits. Query-plan structures are intentionally retained as backend-specific provenance rather than forced into fake equivalence.

### Tradeoffs and limitations

- PostgreSQL is opt-in and requires a server, DSN, and schema privileges.
- The PostgreSQL loader currently rematerializes a configured schema; use a dedicated schema and loader role.
- Compose uses one local demo role. Production should separate a schema-owning loader role from a SELECT-only application role.
- Cross-engine floating-point values are normalized, but larger scientific parity suites may need explicit tolerances.
- SQLite audit and manifest stores remain local even when analytical execution uses PostgreSQL.
- PostgreSQL metadata storage, high-availability connections, pooling, TLS policy, credential rotation, and migrations are future production hardening.
- Dialect-specific reference curriculum queries using `julianday` remain SQLite examples; governed curated queries are portable.
- Relationship-policy enforcement remains disabled.
- No Spark, Airflow, Kubernetes, object storage, Parquet, Delta, or raw/bronze/silver/gold implementation was added.

### How PostgreSQL prepares for the data lake and Spark

PostgreSQL gives a future gold layer a production-style serving destination. It does not become the raw lake and does not replace transformation lineage. The next abstraction will define raw, bronze, silver, and gold storage contracts around batches, manifests, parent snapshots, validation, and publication.

```mermaid
flowchart LR
 RAW["Future raw immutable batch"] --> BR["Future bronze snapshot"]
 BR --> SI["Future silver validated snapshot"]
 SI --> GO["Future gold governed snapshot"]
 GO --> PG["PostgreSQL serving snapshot"]
 GO --> SQ["SQLite compatibility snapshot"]
 PG --> AN["Bounded analysis"]
 SQ --> AN
```

Spark will later transform registered inputs into registered outputs using deterministic reviewed code. PostgreSQL proves the serving boundary now; it does not authorize arbitrary model-generated distributed code. Airflow and Kubernetes remain later concerns.

#### What this means in plain English

PostgreSQL is the future store counter where polished products can be served. The next milestone designs the warehouse shelves and quality stages. Spark may later move and process boxes; it does not decide what is safe to sell.

## Project evolution: from bounded analyst to versioned data platform

The project now has two independently useful boundaries. The application boundary authorizes bounded analysis against either SQLite or PostgreSQL. The new data boundary moves the same logical synthetic records through raw, bronze, silver, and gold snapshots before loading an analytical serving database. Existing API, UI, seed, safety, privacy, metrics, statistics, audit, and benchmark behavior remains compatible.

```mermaid
timeline
 title Project release evolution
 section Completed
  Bounded analyst : deterministic safeguards and SQLite
  Platform seams : query backends, logical records, manifests, snapshots
  Dual serving : optional PostgreSQL and parity contracts
  Local lake : raw, bronze, silver, gold, quality gates, lineage
 section Future
  Distributed transforms : PySpark contract implementation
  Scheduling : Airflow orchestration
  Operations : Kubernetes deployment
```

### What this means in plain English

The original analyst answered governed questions from one dependable local database. It can now receive a shipment of source data, preserve the unopened shipment, clean and validate successive copies, publish an approved analytical edition, and serve that edition from either of two databases.

## Actual live PostgreSQL verification results

The required startup command was identified and attempted on August 5, 2026:

```powershell
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build
```

Compose configuration validation passed, and Docker CLI 29.4.1 was installed. Live startup did **not** succeed. The Docker API pipe `npipe:////./pipe/docker_engine` did not exist because `com.docker.service` was stopped. A direct service-start attempt failed with `Cannot open com.docker.service service on computer '.'`; the process also lacked permission to read `C:\Users\tommy\.docker\config.json`. Therefore no claim of live PostgreSQL health, fixture loading, API smoke testing, benchmark timing, or parity is made from this environment.

The psycopg orchestration tests pass without a server. The live suite remains opt-in and now includes the reusable backend contract, loader, identities, curated analytical parity, and a seven-question machine-readable report. When Docker Desktop is running:

```powershell
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build
$env:CLINICAL_SQL_TEST_POSTGRES_DSN="postgresql://clinical_loader:synthetic-local-only@localhost:5432/clinical"
python -m pytest tests/test_postgres_integration.py -v
```

Inspect health and logs with:

```powershell
docker compose -f docker-compose.yml -f docker-compose.postgres.yml ps
docker compose -f docker-compose.yml -f docker-compose.postgres.yml logs postgres postgres-seed api
```

The current Compose demo role owns the synthetic schema. Query execution still starts a read-only transaction and the live contract attempts mutations to prove enforcement. Production must use a separate schema-owning loader role and a SELECT-only application role.

### What this means in plain English

The PostgreSQL vehicle and its road test are built, but the garage door could not be opened on this machine. Mock and configuration checks succeeded; the README deliberately does not relabel them as a live drive.

## Current dual-backend application architecture

```mermaid
flowchart TD
 UI["Unchanged FastAPI and Streamlit contracts"] --> AG["Bounded analyst workflow"]
 AG --> AU["SQL, privacy, metric, and statistics authorization"]
 AU --> QB{"Configured query backend"}
 QB --> SQ["SQLite compatibility serving snapshot"]
 QB --> PG["Optional PostgreSQL serving snapshot"]
 SQ --> EV["Normalized evidence"]
 PG --> EV
 EV --> AN["Grounded answer and audit"]
```

Switching remains configuration-only:

```env
DATABASE_BACKEND=sqlite
```

or:

```env
DATABASE_BACKEND=postgres
POSTGRES_DSN=postgresql://user:password@host:5432/clinical
CLINICAL_SQL_POSTGRES_SCHEMA=public
CLINICAL_SQL_METADATA_PATH=data/generated/postgres.metadata.db
```

### What this means in plain English

The same application logic, safeguards, and logical dataset work against two different databases. The database driver changes; the authorization checkpoint does not.

## What a data lake is

A data lake is durable storage for data at several stages of readiness. Unlike the analytical serving database, it keeps source-shaped evidence and intermediate versions rather than only the final query-friendly tables. This implementation is deliberately small: canonical JSON Lines files, typed metadata, checksums, and atomic local publication.

### What this means in plain English

Think of the lake as a set of labeled archive shelves. The raw shelf keeps the envelope exactly as delivered. Bronze opens and reads it. Silver corrects and checks a working copy. Gold holds the approved tables used for analysis.

## Why raw, bronze, silver, and gold layers exist

```mermaid
flowchart LR
 GEN["Logical synthetic records"] --> BATCH["Source batch"]
 BATCH --> RAW["Raw: immutable received bytes"]
 RAW --> BR["Bronze: parsed records plus errors"]
 BR --> SI["Silver: cleaned, deduplicated, validated"]
 SI --> GO["Gold: analytics-ready governed tables"]
 GO --> SERVE["SQLite or PostgreSQL serving snapshot"]
 SERVE --> AGENT["Bounded SQL agent"]
```

### What happens in each layer

- **Raw** stores immutable JSON Lines objects, source identity, generator version, parameters, row counts, timestamps, and SHA-256 checksums. Malformed source bytes are preserved.
- **Bronze** parses each row and records parse failures. It does not silently discard problems or claim that malformed input is clean.
- **Silver** applies explicit entity keys, removes duplicate or invalid identifiers, checks categorical domains and references, and records rejected counts.
- **Gold** verifies required analytical entities, registered rate bounds, numerator/denominator consistency, and the synthetic-identifier policy before publication.

### What would happen without each layer

- Without raw, a correction could erase evidence of what arrived.
- Without bronze, parsing failures would be mixed with business-quality failures.
- Without silver, every metric would repeatedly clean identifiers, categories, and references differently.
- Without gold, serving databases could receive tables that are technically parseable but analytically unsafe.

### What this means in plain English

A malformed date enters raw unchanged. Bronze reports that it cannot parse the row. Silver never receives a falsely “fixed” value; after a reviewed correction arrives in a new batch, silver can standardize it. Gold excludes rejected data from registered rates. An audit can still point back to the original source batch.

## Source batches and immutable raw data

A `SourceBatch` identifies the source system, dataset, fixture profile, generator version, parameters, source objects, checksums, counts, disclaimer, and optional parent batch. The CLI supports initial, incremental, and intentionally malformed batches. Raw objects are content-addressed and immutable: the same identifier plus the same bytes is idempotent; conflicting bytes are rejected.

```mermaid
flowchart LR
 SS["Source system"] --> SB["Source batch"]
 SB --> O1["patients.jsonl + checksum"]
 SB --> O2["encounters.jsonl + checksum"]
 SB --> ON["other entity objects + checksums"]
 O1 --> RM["Raw manifest"]
 O2 --> RM
 ON --> RM
```

### What this means in plain English

If a sender later corrects a file, the platform creates a new batch instead of quietly replacing history. “What did we receive?” remains answerable.

## Transformation versions and deterministic execution

`source-to-raw`, `raw-to-bronze`, `bronze-to-silver`, and `silver-to-gold` each have a version. Snapshot identity includes the transformation version, parent, object checksums, and validation evidence. Identical inputs and versions produce identical identifiers. Changing a version produces a different manifest even if rows happen to match.

The implementation uses reviewed ordinary Python. An LLM cannot select, rewrite, or execute transformation code. The invariant remains: **the AI proposes; deterministic software authorizes, executes, verifies, suppresses, and audits.**

### What this means in plain English

The recipe number is printed on every output. Re-running recipe 1.0 on the same ingredients gives the same labeled product. Recipe 2.0 gets a new label even when a small test happens to taste the same.

## Candidate versus published snapshots

Objects are first written through a staging directory. A candidate manifest is registered, deterministic quality checks run, and only a validated candidate atomically replaces the active pointer. Published files are never assembled piece by piece in front of readers.

```mermaid
flowchart TD
 IN["Active parent snapshot"] --> ST["Write candidate objects in staging"]
 ST --> CM["Register candidate manifest"]
 CM --> Q{"Quality gates pass?"}
 Q -->|yes| AT["Atomic active-pointer replacement"]
 AT --> NEW["New active snapshot"]
 Q -->|no| FAIL["Failed run and diagnostics"]
```

### Why failed data must not replace validated data

```mermaid
flowchart LR
 OLD["Previously active validated bronze"] --> READ["Readers continue using it"]
 BAD["Malformed raw candidate"] --> GATE["Bronze parse gate fails"]
 GATE --> DIAG["Rejected rows and warnings retained"]
 GATE -. "no activation" .-> READ
```

A failed run has a manifest and diagnostics but no active snapshot. The prior active snapshot remains selected. Privacy and SQL safeguards are downstream controls and are never weakened to make a data candidate pass.

### What this means in plain English

The new edition is printed and inspected backstage. If pages are missing, the bookstore keeps selling the last approved edition and retains the inspection report.

## Local filesystem lake architecture

`LakeStore` defines object reads/writes/listing, existence and checksum validation, manifest registration and lookup, snapshot publication, and parent traversal. `LocalFilesystemLakeStore` is the only implementation. It rejects absolute paths and `..`, uses deterministic repository-relative object names, writes temporary files followed by atomic rename, separates staging, and exposes no absolute path through its models.

Generated lake contents live under `data/lake/` by default and are ignored by Git. Tests always use temporary roots.

### Why local storage is used before cloud object storage

Local files prove semantics without cloud credentials, network failures, SDKs, billing, or vendor policy. A future object-store implementation must preserve the same content checksums, immutable raw writes, conditional publication, and manifest contract.

### What this means in plain English

Before renting a warehouse, the project proves its labeling, inventory, and inspection process in a controlled room.

## How gold loads into SQLite and PostgreSQL

The serving adapter reads only a validated active gold snapshot, reconstructs the existing typed logical record batches, and invokes the existing transactional loaders. The logical dataset and manifest identity remain stable; the storage identity, backend, and gold parent create a distinct serving snapshot.

```mermaid
flowchart LR
 GO["Validated active gold snapshot"] --> LR["Existing logical record batches"]
 LR --> SL["Transactional SQLite loader"]
 LR --> PL["Transactional PostgreSQL loader"]
 SL --> SS["SQLite serving snapshot + gold parent"]
 PL --> PS["PostgreSQL serving snapshot + gold parent"]
 SS --> SQL["Authorized SQL"]
 PS --> SQL
```

### What this means in plain English

Gold is the approved manuscript. SQLite and PostgreSQL are two editions printed from it. Each edition has its own inventory ID but points to the same approved manuscript and source history.

## Complete lineage from source object to final answer

```mermaid
flowchart RL
 ANSWER["Evidence-grounded answer"] --> AUDIT["Analysis audit and validated SQL"]
 AUDIT --> DB["Serving database snapshot"]
 DB --> GOLD["Gold snapshot"]
 GOLD --> SILVER["Silver snapshot"]
 SILVER --> BRONZE["Bronze snapshot"]
 BRONZE --> RAW["Raw snapshot"]
 RAW --> BATCH["Source batch"]
 BATCH --> OBJECTS["Immutable source objects and checksums"]
```

`LineageResolver` can optionally receive the lake store. It resolves an analysis run to its serving snapshot, reads `gold_snapshot_id`, and traverses deterministic parent links to raw. Transformation name, version, checksums, validation, and source identity are platform metadata—not model prose. Placeholder orchestration and distributed-job IDs remain null.

### What this means in plain English

When an answer says “300 patients,” the platform can identify the SQL run, database copy, gold tables, every cleaning stage, source batch, and exact checksummed source objects behind that number.

## Beginner-friendly local pipeline walkthrough

Use a small test profile and an isolated lake directory:

```powershell
python -m src.lake.cli --root data/lake generate-source --profile test --seed 17
python -m src.lake.cli --root data/lake publish-raw --batch-id <batch-id>
python -m src.lake.cli --root data/lake transform --input-snapshot-id <raw-snapshot-id> --to bronze
python -m src.lake.cli --root data/lake transform --input-snapshot-id <bronze-snapshot-id> --to silver
python -m src.lake.cli --root data/lake transform --input-snapshot-id <silver-snapshot-id> --to gold
python -m src.lake.cli --root data/lake validate --manifest-id <gold-manifest-id>
python -m src.lake.cli --root data/lake publish-sqlite --gold-snapshot-id <gold-snapshot-id> --path data/generated/lake-serving.db
python -m src.lake.cli --root data/lake lineage --snapshot-id <gold-snapshot-id>
```

The convenience command performs the same visible stages:

```powershell
python -m src.lake.cli --root data/lake run-pipeline --profile test --seed 17
python -m src.lake.cli --root data/lake list --layer gold
```

PostgreSQL publication is explicit:

```powershell
python -m src.lake.cli --root data/lake publish-postgres --gold-snapshot-id <gold-snapshot-id> --metadata-path data/generated/postgres.metadata.db
```

Create quality-gate fixtures with `generate-source --malformed`. Create a related batch with `--kind incremental --parent-batch-id <batch-id>`. These commands never change the historical `python -m src.database.seed` behavior.

### What this means in plain English

Each command is one inspectable factory station. `run-pipeline` is a shortcut, not a hidden alternative process.

## Why Spark is not included yet

Spark solves distributed computation; it should not decide what raw, bronze, silver, gold, validation, or publication mean. This milestone first freezes those contracts with small deterministic Python.

```mermaid
flowchart LR
 CONTRACTS["Existing layer and validation contracts"] --> LOCAL["Current local Python implementation"]
 CONTRACTS --> SPARK["Future PySpark implementation"]
 LOCAL --> PARITY["Same-input parity suite"]
 SPARK --> PARITY
 PARITY --> PUBLISH["Only validated equivalent outputs publish"]
```

This release now implements that optional PySpark boundary while retaining local Python as the compatibility fixture. Airflow orchestration is the next milestone.

### What this means in plain English

The project wrote and tested the recipe before buying industrial kitchen equipment. Spark can later cook larger batches without changing the recipe or inspection form.

## Why Airflow is not included yet

Airflow schedules known work; it should not define transformation rules. Once local and PySpark implementations satisfy the same contracts, Airflow can call them, retry operational failures, and record its run ID in the existing optional field.

```mermaid
flowchart TD
 AF["Future Airflow schedule"] --> R["Generate/register raw batch"]
 R --> B["Invoke reviewed bronze transform"]
 B --> S["Invoke reviewed silver transform"]
 S --> G["Invoke reviewed gold transform"]
 G --> P["Publish serving snapshot after gates"]
```

### What this means in plain English

Airflow will become the timetable and dispatcher. It will not rewrite the trains or decide whether unsafe cargo passes inspection.

## Why Kubernetes remains last

Kubernetes operates multiple mature services. It is useful after storage, processing, scheduling, health, secrets, resources, and ownership boundaries exist.

```mermaid
flowchart TD
 K["Future Kubernetes cluster"] --> API["Stateless API replicas"]
 K --> UI["UI service"]
 K --> AF["Airflow components"]
 K --> SP["Spark operator/workers"]
 API --> PG["Managed PostgreSQL serving"]
 AF --> OBJ["Object storage lake"]
 SP --> OBJ
```

This is a future topology, not code or deployment added by this release.

### What this means in plain English

Kubernetes is the building manager. The project first defines the rooms, machines, schedules, and safety procedures that the manager will operate.

## Verification, parity, and benchmark results

The final local run produced:

- **156 passed, 16 skipped**: 13 require the unavailable live PostgreSQL DSN and 3 require a real Java/PySpark runtime;
- **92.97% coverage**, above the 92% gate;
- successful compilation of `src` and `tests`;
- valid original and PostgreSQL-overlay Compose configurations;
- test lake profile: 300 patients and 1,200 encounters, validated through gold and published to SQLite;
- demo lake profile: 2,500 patients and 10,000 encounters, validated through gold;
- resolved serving lineage layers: gold → silver → bronze → raw;
- eight benchmark cases with 100% table-selection accuracy, 100% clarification accuracy, and 100% unsafe-query rejection.

The suite covers deterministic reruns, version-sensitive identities, path traversal, atomic writes, raw immutability, checksums, serialization, manifest conflicts, all three transforms, composite-key preservation, quality-gate failure, prior-active preservation, gold-to-SQLite and mocked-loader PostgreSQL publication boundaries, and analysis-audit-to-raw lineage.

The PostgreSQL parity report contains query ID, question, both statuses, exact normalized result equality, numeric tolerance, warning equality, answer equality or explanation, both timings, snapshot IDs, dataset ID, and manifest ID. It covers aggregation, CTE/rate logic, multi-table joins, privacy/cohort behavior, statistics, clarification, and denial. It is generated only during a live run; no fabricated report is committed.

Performance comparisons require equivalent snapshots, cache-state labels, server configuration, and network context. Local SQLite and an unavailable Docker daemon cannot produce a meaningful database speed comparison.

## Troubleshooting

- **Docker pipe missing:** start Docker Desktop, confirm `docker version` shows a Server section, then rerun Compose.
- **Cannot open Docker service:** use an account allowed to start Docker Desktop or start it interactively; this repository cannot bypass Windows service policy.
- **PostgreSQL test skipped:** set `CLINICAL_SQL_TEST_POSTGRES_DSN` and confirm the database accepts connections.
- **PostgreSQL schema permission error:** use a dedicated empty schema owned by the loader role.
- **Unsafe lake path:** pass a configured root and platform-generated identifiers; absolute paths and `..` are rejected inside object metadata.
- **Checksum failure:** do not edit published objects. Register a corrected source batch.
- **Bronze gate fails:** inspect warnings and rejected-row counts; raw remains preserved.
- **Candidate did not activate:** inspect its `ValidationResult`; the previous active snapshot is intentionally retained.
- **PostgreSQL publication missing DSN:** pass `--dsn` or set `POSTGRES_DSN`.

## Tradeoffs, limitations, and production-hardening roadmap

- JSON Lines is transparent and dependency-free but larger and slower than Parquet.
- Local atomic rename is not a distributed transaction and assumes one controlled filesystem.
- The current source adapter is synthetic; real ingestion authorization and PHI controls remain future work.
- Silver checks are intentionally focused on this fixture, not a generic enterprise quality framework.
- Retention and garbage collection are manual.
- PostgreSQL live results remain blocked until Docker or a DSN is available.
- No Spark, Airflow, Kubernetes, cloud SDK, object-storage server, table format, or relationship-policy enforcement was added.

Production hardening should add an object-store adapter with conditional writes and encryption; Parquet after a dependency/format ADR; identity and access controls; PHI classification; tamper-evident metadata; retention; observability; live PostgreSQL roles/TLS/pooling; and disaster recovery. PySpark is next. Airflow follows stable Spark jobs. Kubernetes remains last.

### What this means in plain English

This release proves the chain of custody and quality process on one machine. It does not pretend that a local folder is a globally durable production lake.

## Optional PySpark transformation engine

### What changed in this milestone

The raw/bronze/silver/gold contracts now have a narrow execution boundary with two implementations:

- `LocalPythonTransformationEngine` wraps the existing Python behavior and remains the default and compatibility oracle.
- `PySparkTransformationEngine` executes the same reviewed transitions in local Spark mode and writes Parquet candidates.

Spark is installed only with `pip install -e ".[spark,dev]"`. It does not participate in `/analyze`, SQL authorization, privacy decisions, metric definitions, statistical approval, or answer grounding. Existing API and UI contracts are unchanged.

```mermaid
flowchart TD
 CLI["Lake CLI or registered batch job"] --> E{"Transformation engine"}
 E -->|default| PY["Canonical local Python engine"]
 E -->|optional| SP["PySpark engine"]
 PY --> C["Shared lake manifests and quality policy"]
 SP --> C
 C --> P["Atomic validated publication"]
```

#### What this means in plain English

The project now has a small workshop implementation and an optional industrial-style implementation of the same recipe. Spark receives work only after deterministic software selects a registered transformation.

### What Apache Spark is

Apache Spark is a distributed data-processing engine. It represents tabular work as DataFrames, divides records into partitions, builds a lazy execution plan, and runs tasks on executors coordinated by a driver. This repository initially uses local mode, so those roles run on one developer machine while retaining Spark's programming model.

#### What this means in plain English

Spark is a foreman that divides a large job into work packets. Local mode puts the foreman and workers in one building; a cluster later places the workers on many machines.

### Why Spark was introduced after the lake contracts

Raw immutability, layer meanings, validation results, identities, parentage, and atomic publication already existed before Spark. This prevents an execution engine from quietly becoming the policy definition.

```mermaid
timeline
 title Project evolution
 Bounded SQL analyst : SQLite and deterministic safeguards
 Platform boundaries : Backends, manifests, snapshots, audit lineage
 Local medallion lake : Python raw, bronze, silver, gold
 Current : Optional Spark implementation and parity
 Next : Airflow scheduling
 Later : Kubernetes operations
```

#### What this means in plain English

The recipe and inspection checklist existed before the larger machine arrived. The machine must reproduce them; it cannot rewrite them.

### Python reference engine versus Spark engine

| Concern | Python reference | PySpark |
|---|---|---|
| Default | Yes | No |
| Installation | Standard project dependencies | `.[spark]`, Java 17 recommended |
| Output | Canonical JSON Lines | Parquet plus canonical logical sidecar |
| Execution | One Python process | Spark driver and local executors |
| Policy | Shared deterministic checks | Same shared deterministic checks |
| Identity | Logical content and transformation | Same logical identity comparison; engine-specific snapshot |
| Best use | CI, compatibility, small data | Larger local batches and future cluster execution |

Only physical format, part layout, execution time, Spark application ID, engine metadata, and engine-specific snapshot identity may differ. Normalized rows, counts, warnings, rejected counts, validation, dataset identity, and lineage structure must agree.

#### What this means in plain English

The Python and Spark editions may use different packaging, but the chapters, totals, rejected pages, and approval outcome must match.

### Spark DataFrames, sessions, drivers, and executors

A **DataFrame** is a distributed table with named typed columns and a query plan. A **Spark session** is the controlled entry point that configures the application, timezone, shuffle partitions, and master. The **driver** builds plans and coordinates work. **Executors** run tasks over partitions.

```mermaid
flowchart TD
 SESSION["SparkSession: UTC, master, partitions"] --> DRIVER["Driver: build reviewed transformation plan"]
 DRIVER --> E1["Executor task: partition 1"]
 DRIVER --> E2["Executor task: partition 2"]
 DRIVER --> EN["Executor task: partition N"]
 E1 --> OUT["Partitioned Parquet candidate"]
 E2 --> OUT
 EN --> OUT
```

No Spark session is created during import. `SparkSessionFactory` validates configuration, reports missing Java/PySpark clearly, reuses its session within a command, and stops it afterward.

#### What this means in plain English

The session is the job site's controlled power switch. Importing a Python module does not secretly start the machinery.

### Local mode versus a real cluster

`local[*]` uses available cores on one machine. A cluster master would distribute executors across machines. Local mode proves APIs, schemas, transformations, publication, and lineage; it does not prove network behavior, resilience, or cluster-scale speed.

```env
CLINICAL_SQL_LAKE_TRANSFORM_ENGINE=spark
CLINICAL_SQL_SPARK_MASTER=local[*]
CLINICAL_SQL_SPARK_SHUFFLE_PARTITIONS=4
CLINICAL_SQL_SPARK_LOG_LEVEL=WARN
```

#### What this means in plain English

Local mode is a full dress rehearsal on one stage, not evidence that a stadium production will have the same performance.

### Lazy evaluation, transformations, and actions

Spark transformations such as filtering, projection, and deduplication describe work lazily. Actions such as `count`, `collect`, and Parquet writes cause Spark to execute the plan. This implementation keeps actions at explicit reconciliation, canonicalization, validation, and publication boundaries.

Narrow transformations can process each partition mostly independently. Wide transformations—such as deduplication by key—may require a shuffle that moves related keys together.

```mermaid
flowchart LR
 P1["Partition 1: patient 1, 3"] --> SH["Shuffle by patient key"]
 P2["Partition 2: patient 1, 2"] --> SH
 SH --> O1["Output partition: patient 1"]
 SH --> O2["Output partition: patient 2, 3"]
```

#### What this means in plain English

Writing instructions on a whiteboard is lazy planning. An action tells the crew to perform them. A shuffle is the expensive moment when workers exchange boxes so matching labels meet.

### Partitions and shuffles

Partitions are Spark's units of parallel work. Their count affects task overhead, memory, and output files. Shuffle partition count is controlled through configuration. Output partition count is recorded in `TransformationRun`; it is operational metadata, not metric or dataset identity.

Wide operations can be necessary for correct composite-key deduplication. They are never introduced by model-generated expressions.

### Why explicit schemas matter

`spark_schemas.py` defines every logical field, nullability rule, numeric representation, identifier, date/timestamp string, and physical metadata column for all eleven entities. Spark does not infer a patient ID as text merely because one file contains nulls.

Physical Parquet includes `_lake_row_order`, source batch ID, record hash, quality flags, and rejection metadata. Canonical logical rows exclude these operational columns before parity and serving.

#### What this means in plain English

The receiving form says which box holds an integer, date text, optional value, or flag. Spark cannot guess a different form from a small sample.

### Why Spark writes multiple Parquet files

Spark normally writes one `part-*` file per output partition plus control files. Those names can change with task scheduling. The platform therefore writes a canonical logical sidecar and calculates the logical checksum from sorted normalized records, canonical field ordering, entity, input parent, transformation version, engine, and format.

```mermaid
flowchart TD
 DF["One logical DataFrame"] --> A["part-00000.parquet"]
 DF --> B["part-00001.parquet"]
 DF --> S["_SUCCESS"]
 DF --> L["Canonical _logical.jsonl"]
 L --> H["Stable logical checksum"]
 A -. "not identity" .-> H
 B -. "not identity" .-> H
```

Part names, directory enumeration order, Spark application ID, and timing do not define logical equality. Engine and format do participate in physical object and snapshot identity so provenance remains honest.

#### What this means in plain English

The same book may be shipped in two boxes today and three tomorrow. Box labels do not change the book's text, but the shipping record still says how it was packaged.

### Spark raw to bronze

The engine validates raw checksums, parses canonical JSON Lines, applies explicit entity schemas, records source batch and record hashes in physical metadata, preserves source values, reports malformed lines, detects duplicate source objects, reconciles expected keys, writes a Parquet candidate, and invokes the shared bronze gate.

```mermaid
flowchart LR
 RAW["Immutable raw JSONL"] --> CK["Checksum and parse"]
 CK --> DF["Explicit-schema DataFrame"]
 DF --> META["Batch, order, record hash metadata"]
 META --> PQ["Bronze Parquet candidate"]
 PQ --> GATE["Shared bronze gate"]
```

One malformed date-like source line remains in raw. A syntactically malformed line is reported and excluded from bronze logical rows; the failed gate prevents activation. Nothing is silently relabeled as valid.

#### What this means in plain English

Spark opens the preserved envelope and fills a typed intake form. If a line cannot be read, the error is attached to the inspection record and the candidate does not replace the approved shelf.

### Spark bronze to silver

Spark applies non-null identifier requirements and entity-specific simple or composite-key deduplication. The central silver policy performs real ISO date parsing, categorical-domain checks, identifier checks, missingness checks, and referential reconciliation. Rejected counts are compared with Python.

A genuine reference bug was fixed here: the prior date check recognized only the visual `YYYY-MM-DD` shape, so `2025-99-99` could pass. Both engines now use real ISO parsing. Valid frozen snapshot identities remain unchanged.

#### What this means in plain English

A label that looks like a date is no longer enough; the calendar date must actually exist. Both machines use the same calendar test.

### Spark silver to gold

Spark carries validated entity rows into analytics-ready Parquet and invokes the existing gold rules: required entities, numerator no greater than denominator, rates within zero and one, registered metric compatibility, and synthetic-identifier policy. Spark does not own a separate metric formula registry.

```mermaid
flowchart LR
 SI["Validated Spark silver"] --> GO["Gold DataFrames"]
 REG["Existing metric registry and quality policy"] --> CHECK["Deterministic reconciliation"]
 GO --> CHECK
 CHECK -->|pass| PUB["Atomic gold activation"]
 CHECK -->|fail| KEEP["Keep prior active gold"]
```

#### What this means in plain English

Spark can add the columns quickly, but the project's existing rulebook decides whether the totals and rates are publishable.

### Candidate publication, interruption, and rollback

Spark writes into the lake staging directory. Only complete Parquet output receives its canonical sidecar and moves to a published object path. The manifest is registered, quality gates run, and the active pointer changes only on success. A write exception removes partial staging and leaves the previous active snapshot untouched.

```mermaid
flowchart TD
 OLD["Current active snapshot"] --> READ["Readers"]
 JOB["Spark candidate job"] --> STAGE["Staging Parquet"]
 STAGE --> Q{"Write and quality pass?"}
 Q -->|yes| ATOM["Atomic object and active-pointer publication"]
 ATOM --> NEW["New active snapshot"]
 Q -->|no| CLEAN["Clean partial staging; retain diagnostics"]
 CLEAN -.-> READ
```

#### What this means in plain English

A power failure while printing a new edition cannot remove the approved edition from the shelf.

### Python and Spark parity

The parity framework runs separate stores from identical source inputs, normalizes every row, sorts logical record representations, and hashes content independently of Parquet part names. It compares status, schemas, counts, hashes, rejected rows, warnings, validation, dataset identity, and parentage.

```mermaid
flowchart TD
 SOURCE["Identical source batch"] --> PY["Python pipeline"]
 SOURCE --> SP["Spark pipeline"]
 PY --> PN["Normalized logical rows and validation"]
 SP --> SN["Normalized logical rows and validation"]
 PN --> CMP["Machine-readable parity report"]
 SN --> CMP
 CMP --> DEC{"All required fields equal?"}
```

Covered contract cases include normal test data, deterministic retry, incremental source identity, malformed input, invalid dates, duplicate keys, referential inconsistency, failed publication preservation, registered rates, serving publication, and lineage. Real Spark execution is a separately skipped integration test when Java/PySpark is absent; fake-runtime tests exercise orchestration deterministically without masquerading as a real Spark runtime.

#### What this means in plain English

Both factories receive the same materials. Inspectors compare the products after removing shipping labels and timing stickers.

### Spark gold to SQLite or PostgreSQL

Spark gold uses the existing serving adapters. Canonical logical sidecars reconstruct the existing typed record batches; SQLite and PostgreSQL loaders do not learn Spark-specific policy. The serving snapshot records the exact Spark gold parent.

```mermaid
flowchart LR
 SG["Validated Spark gold snapshot"] --> B["Canonical logical batches"]
 B --> SQ["SQLite loader"]
 B --> PG["PostgreSQL loader"]
 SQ --> A["Bounded analyst"]
 PG --> A
 A --> AUD["Audit with serving and gold lineage"]
```

#### What this means in plain English

Spark prepares the approved manuscript. The same established printers produce the SQLite or PostgreSQL edition, and the receipt names the manuscript used.

### Complete Spark lineage to a final answer

```mermaid
flowchart RL
 ANSWER["Grounded answer"] --> AUDIT["Audit and validated SQL"]
 AUDIT --> SERVE["Serving snapshot"]
 SERVE --> GOLD["Spark gold + application metadata"]
 GOLD --> SILVER["Spark silver"]
 SILVER --> BRONZE["Spark bronze"]
 BRONZE --> RAW["Immutable raw snapshot"]
 RAW --> BATCH["Source batch and checksummed objects"]
```

Transformation runs add execution engine, engine version, application ID, master, partitions, records read/written/rejected, physical format, implementation version, and timestamps. These values come from runtime objects, never the LLM. API responses expose no paths, secrets, raw records, or unbounded Spark logs.

### Installation and Java setup

Supported project Python is 3.11 or newer. The optional dependency supports PySpark `>=3.5,<4.1`; Java 17 is the recommended common runtime.

```bash
pip install -e ".[spark,dev]"
python -m src.lake.cli spark-capability
```

On Windows, install a 64-bit JDK 17, set `JAVA_HOME` to the JDK directory, add `%JAVA_HOME%\bin` to `PATH`, open a new terminal, and verify `java -version`. Avoid pointing `JAVA_HOME` at the `bin` directory itself.

On macOS/Linux, install JDK 17 with the platform package manager, export `JAVA_HOME` using the JDK's documented location, add `$JAVA_HOME/bin` to `PATH`, and verify both Java and `python -c "import pyspark"`.

#### What this means in plain English

PySpark is the Python control package; Java runs the Spark engine underneath. Both must be installed before a real Spark session can start.

### Spark CLI workflow

Python remains explicit and default:

```bash
python -m src.lake.cli --root data/lake run-pipeline --profile test --engine python
```

Run individual Spark stages:

```bash
python -m src.lake.cli --root data/lake transform --input-snapshot-id <raw-id> --to bronze --engine spark
python -m src.lake.cli --root data/lake transform --input-snapshot-id <bronze-id> --to silver --engine spark
python -m src.lake.cli --root data/lake transform --input-snapshot-id <silver-id> --to gold --engine spark
```

Run the full Spark path or parity report:

```bash
python -m src.lake.cli --root data/lake run-pipeline --profile test --engine spark
python -m src.lake.cli --root data/lake parity --profile test --report data/parity-reports/test.json
```

Existing `validate`, `lineage`, `publish-sqlite`, and `publish-postgres` commands work for Spark snapshots without a separate serving path.

### Performance demonstration and limitations

The optional `spark-scale` profile contains 50,000 patients and 200,000 encounters. It is excluded from ordinary CI:

```bash
python -m src.lake.cli --root data/spark spark-performance --profile spark-scale
```

The command records elapsed time, row counts through the gold manifest, snapshot ID, engine metadata, and whether execution was local. Compare Python and Spark only on equivalent hardware, cache state, partitions, Java/Python versions, and inputs. Local mode has startup and driver-canonicalization costs and does not prove Spark is faster or cluster-scalable.

#### What this means in plain English

The large profile is a load test switch, not a marketing benchmark. One laptop run cannot predict a production cluster.

### Spark troubleshooting

- **`Install .[spark]`:** install the optional group; default installs intentionally omit PySpark.
- **Java not found:** install JDK 17 and correct `JAVA_HOME`/`PATH`.
- **Unsupported version:** use PySpark 3.5.x or 4.0.x; the application rejects outside `>=3.5,<4.1`.
- **Gateway exited:** check `java -version`, architecture, `JAVA_HOME`, and spaces/permissions in temporary directories.
- **Malformed master:** use `local[*]`, `local[2]`, or a reviewed cluster master.
- **Schema mismatch:** inspect the candidate validation and explicit entity schema; do not enable inference.
- **Parquet write failure:** staging is cleaned and the previous active snapshot remains.
- **Candidate did not activate:** inspect rejected rows, warnings, and deterministic checks.
- **Unexpected parity difference:** compare logical hashes and schemas before examining physical part files.
- **Windows file locks:** stop the Spark session and ensure no explorer/process holds the staging directory.

The current verification environment has no `java` command, no `JAVA_HOME`, and no installed PySpark. Real Spark integration and performance tests are therefore skipped, not reported as passed. PyArrow is available, but it is not a substitute for Spark execution. Docker/PostgreSQL remains blocked by the stopped Docker daemon described earlier.

### Why the LLM cannot generate arbitrary Spark code

Only named reviewed methods implement the three transitions. Spark receives typed data and fixed operations after CLI/configuration selection. The LLM cannot submit Python, SQL expressions, UDFs, JARs, or cluster jobs. Spark cannot approve SQL, alter metric definitions, lower quality thresholds, classify privacy, or expose raw records.

#### What this means in plain English

The AI may ask for an analysis later; it cannot walk onto the factory floor and reprogram the machinery.

### Why Airflow is still deferred

Airflow will schedule these established Python/Spark commands, retries, and publication dependencies after real Spark parity is available. It will populate `orchestration_run_id`; it will not embed alternate transformation policy.

```mermaid
flowchart LR
 AF["Future Airflow DAG"] --> RAW["Register raw"]
 RAW --> BR["Run selected bronze engine"]
 BR --> SI["Run selected silver engine"]
 SI --> GO["Run selected gold engine"]
 GO --> PUB["Publish after existing gates"]
```

### Why Kubernetes is still deferred

Kubernetes follows Airflow, externalized object storage and metadata, independently deployable services, readiness probes, resource limits, secrets, and tested operational behavior.

```mermaid
flowchart TD
 K["Future Kubernetes"] --> API["Analyst API"]
 K --> AIR["Airflow services"]
 K --> SD["Spark driver pods"]
 SD --> EX["Spark executor pods"]
 AIR --> SD
 API --> PG["PostgreSQL serving"]
 SD --> OBJ["External object storage"]
```

No Airflow dependency, DAG, Kubernetes manifest, Spark operator, cloud SDK, Kafka, MinIO, Delta Lake, Iceberg, or Hudi component was added.

### Current limitations and production-hardening roadmap

- Spark logical canonicalization currently collects normalized fixture rows at the driver; future scale requires distributed sorted record-hash aggregation.
- Canonical JSONL sidecars intentionally trade storage duplication for transparent identity and serving compatibility.
- Real Spark parity is unavailable until Java and PySpark are installed.
- Local Parquet atomic rename assumes one filesystem.
- The large profile is optional and not a CI gate.
- PostgreSQL live publication still requires a server.

Production hardening should next add Airflow orchestration only after real Spark parity passes. Later work should add distributed logical hashing, object storage with conditional publication, external metadata, encryption and access policy, Spark event/metrics capture, cluster submission, resource testing, and operational recovery. Kubernetes remains after those boundaries exist.

## Design decisions, limits, and production hardening

SQLite makes the demo portable and inspectable; PostgreSQL should use a dedicated SELECT-only role and statement timeout. Curated SQL makes credential-free behavior reproducible. SQLGlot provides structural checks that regex cannot, though policy remains conservative. FastAPI supplies typed service contracts while Streamlit optimizes portfolio exploration.

Known limits: live planning requires network access, API credit, and access to the configured OpenAI model; relationship validation is conservative; statistics are unadjusted; no causal or clinical inference is intended; benchmark breadth should grow beyond the seed fixture; logistic/linear regression and standardized rates remain registry extensions; SQLite timeouts are cooperative; audit rows are not cryptographically tamper-evident. Production requires identity, authorization, encrypted/tamper-evident audit storage, migrations, PostgreSQL permissions/RLS, monitoring, reviewed metric governance, model/version pinning, red-team evaluation, approval queues, and incident response.

## Resume-ready description

**Agentic Clinical SQL Analyst: Designed a normalized healthcare database and a constrained LangGraph agent that converts natural-language questions into validated read-only SQL, executes multi-table analytics, invokes approved statistical tools, checks result plausibility, repairs failed queries, enforces privacy safeguards, and returns evidence-grounded findings with query provenance and audit trails.**

## Design rationale and technical walkthrough

### Relational database design

The schema is normalized so that each major concept has one authoritative home. Patient attributes belong in `patients`, facility attributes in `hospitals`, provider attributes in `providers`, and visit-level facts in `encounters`. Diagnosis and procedure definitions are stored separately from encounters so the same code and description do not have to be copied into thousands of rows.

An encounter can have multiple diagnoses and procedures, while each diagnosis or procedure can appear in many encounters. The `encounter_diagnoses` and `encounter_procedures` bridge tables model these many-to-many relationships without duplicating either side. Foreign keys prevent bridge records from referring to nonexistent encounters or vocabulary entries. `CHECK` constraints keep flags, categories, counts, costs, and rates within valid ranges, while unique and composite-key constraints prevent logically duplicate relationships.

Indexes are placed on common date filters and join paths, such as encounter admission dates, hospital IDs, patient IDs, diagnosis links, and readmission index encounters. They reduce the amount of data SQLite must scan for common analytical queries. Views such as `encounter_facts` and `hospital_readmission_summary` package frequently reused joins and calculations behind stable, readable interfaces.

Cohort queries explicitly distinguish a primary diagnosis from a secondary or comorbid diagnosis. For example, a heart-failure readmission cohort should not silently include every encounter where heart failure appeared anywhere in the diagnosis list. Requiring `primary_diagnosis_flag = 1` makes the population definition visible, reproducible, and less vulnerable to accidental double counting.

### SQL techniques demonstrated by the project

The annotated files in [`sql/reference_queries`](sql/reference_queries/README.md) progress from basic reporting to cohort construction and longitudinal analysis. Joins connect normalized entities; common table expressions break complicated cohort logic into named stages; and date calculations derive calendar periods, follow-up windows, and length of stay.

`HAVING` applies eligibility rules after aggregation, such as excluding hospitals with fewer than 30 cases. Window functions preserve row-level or period-level detail while adding comparisons across rows. `ROW_NUMBER` selects the latest encounter, `RANK` and `DENSE_RANK` create ordered comparisons, `LAG` compares a quarter with its predecessor, and framed `AVG` expressions calculate rolling averages. The examples also cover subqueries, `CASE`, left joins, parameterized filters, views, indexes, and `EXPLAIN QUERY PLAN`.

### Natural language to SQL as constrained compilation

The application does not treat text-to-SQL as “ask a model for code and run it.” It behaves more like a constrained compiler. First, the user's language is converted into a typed analysis plan containing the metric, population, dates, grouping fields, required tables, privacy tier, and expected output. The model may then propose one SQL candidate that implements that plan.

The candidate is only an untrusted intermediate representation. Deterministic validators decide whether it conforms to the registered metric, approved schema, relationship rules, privacy policy, and resource limits. Only an approved query reaches the read-only executor. This separation lets the model handle linguistic ambiguity without giving it authority over execution.

### Why SQLGlot is used

SQLGlot parses SQL into an abstract syntax tree (AST). The application can therefore inspect the actual statement type and its table references, column references, joins, functions, nesting, selected expressions, and limit clauses. It can also safely rewrite a query to insert a result limit.

Regular expressions are useful for supplemental checks such as detecting comments or obvious administrative keywords, but they do not understand SQL structure, aliases, nested queries, or common table expressions. AST validation is the primary control because it evaluates the parsed meaning of the query rather than relying only on surface text.

### Permissions and resource containment

Validation code can contain defects, so it is not the only boundary. Approved queries run through a SQLite URI connection opened in read-only mode with `query_only` enabled. Even if a future validator bug allowed a write statement through, the database connection would independently refuse the mutation.

Read-only permissions protect data integrity, but a valid `SELECT` can still consume excessive resources. The executor therefore adds row limits, caps query complexity, restricts joins and selected columns, reviews `EXPLAIN QUERY PLAN`, and installs a cooperative timeout. These controls reduce the risk of accidental Cartesian products, result explosions, and expensive scans.

### Why model self-critique is not enough

Asking a model to review its own SQL can improve quality, but it cannot serve as the sole safeguard. Generation and self-review are probabilistic and often share the same assumptions, so a model may confidently approve the same mistake it originally made.

This project keeps permission decisions, metric arithmetic, privacy suppression, and plausibility checks in deterministic code. Model-assisted criticism can be added as a secondary signal, but it cannot override the schema allowlist, read-only connection, fixed metric definitions, or result validators.

### Division of responsibilities

The LLM handles tasks that benefit from language understanding: interpreting the question, detecting ambiguity, selecting a registered metric, producing a structured plan, and proposing a SQL candidate. It may also draft an interpretation from the verified evidence.

Application code retains responsibilities that require predictable enforcement: deciding whether a request is permitted, validating the plan and SQL, controlling database access, performing arithmetic, executing approved statistics, suppressing small cells, checking result plausibility, grounding numeric claims, and writing the audit record. The model proposes; the software authorizes and verifies.

### Statistical reasoning and limitations

Statistical tests are selected according to the question and data shape. Proportion comparisons may use chi-square or Fisher exact tests; continuous two-group comparisons may use a Welch t-test or Mann–Whitney U test; several continuous groups may use ANOVA; and association questions may use Pearson or Spearman correlation. Confidence intervals communicate estimation uncertainty instead of reducing every analysis to a p-value.

Each fixed tool checks data types, minimum sample sizes, missing values, and relevant assumptions. Its output includes warnings and, where appropriate, an effect size or confidence interval. Statistical significance alone does not establish clinical importance or causation. The demo analyses are unadjusted, so apparent differences may reflect age, diagnosis mix, illness severity, hospital size, or other confounders rather than the grouping variable itself.

### Privacy, bounded behavior, and provenance

Small-cell suppression hides calculated values for groups with fewer than 10 observations. High-risk requests for patient-level records or unrestricted exports are denied. Medium-risk demographic analyses are flagged, and follow-up context contains only bounded samples of previously verified aggregate results. These data-minimization rules reduce unnecessary disclosure even though the included dataset is synthetic.

The workflow also has explicit stopping conditions. Ambiguous questions request clarification, validation failures stop execution, and repair paths have finite retry budgets. Every run receives an ID and records its question, typed plan, SQL, validation events, execution status, timing, row count, statistical tools, warnings, answer, and provenance. This structured history makes a result reproducible and reviewable without exposing API keys or hidden reasoning.

### Why the project uses both FastAPI and Streamlit

FastAPI exposes typed, reusable service contracts for analysis, SQL validation, schema discovery, metrics, reference queries, and audit runs. Automatic OpenAPI documentation makes those contracts easy to inspect and allows another frontend or service to use the same backend behavior.

Streamlit provides the interactive portfolio interface. It places the answer, verified result table, chart, metric definition, SQL, validator output, audit trace, schema, and dataset guide in one browser experience. This makes the system's evidence and safety boundaries visible instead of hiding them behind a conversational response.

### Reproducibility and continuous integration

Docker packages the Python runtime, dependencies, source code, and startup commands into a reproducible environment. Docker Compose starts the API and UI together while using a shared volume for generated synthetic data. A reviewer can therefore run the project without manually recreating the local development setup.

GitHub Actions installs the project in a clean Python environment, generates a deterministic test database, runs the pytest suite with coverage reporting, and smoke-runs the benchmark workflow. The pipeline checks that a fresh clone can reproduce the database, import the services, enforce the safeguards, and complete representative analyses.

## Security and clinical disclaimer

This is a defense-in-depth educational prototype, not a security certification. It uses synthetic data only and must not receive PHI. It is not validated for patient care, diagnosis, treatment, operational decisions, regulatory reporting, or hospital comparison. Review SQL, metrics, and outputs with qualified domain experts.

MIT licensed. Contributions are welcome under [CONTRIBUTING.md](CONTRIBUTING.md).
