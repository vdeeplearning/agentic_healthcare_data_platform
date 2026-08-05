# Architecture and diagrams

Each diagram has a short summary for readers who do not use Mermaid rendering.

## 1. Executive end-to-end architecture

The analyst authorizes read-only analytics over governed serving data; lake processing, orchestration, and deployment remain separate layers.

```mermaid
flowchart LR
 Q["Question"] --> AG["Bounded analyst"] --> SAFE["Deterministic authorization"] --> DB["Serving database"] --> ANS["Grounded answer"]
 SRC["Synthetic source"] --> RAW["Raw"] --> BR["Bronze"] --> SI["Silver"] --> GO["Gold"] --> DB
 AF["Airflow"] --> RAW
 AF --> BR
 K["Kubernetes"] -. "deploys" .-> AG
 K -. "deploys" .-> AF
```

## 2. Agent safety and authorization flow

The model proposes; deterministic policy can deny, clarify, or authorize bounded execution.

```mermaid
flowchart TD
 Q["Question"] --> RISK{"Privacy risk"}
 RISK -->|"high"| DENY["Deny"]
 RISK -->|"ambiguous"| CLARIFY["Request clarification"]
 RISK -->|"allowed"| PLAN["Typed plan"] --> SQL["SQL candidate"] --> AST{"AST + schema + complexity valid?"}
 AST -->|"no"| STOP["Stop safely"]
 AST -->|"yes"| READ["Read-only bounded execution"] --> CHECK["Result + grounding checks"] --> ANSWER["Evidence-grounded answer"]
```

## 3. Medallion pipeline

Every transition publishes only validated candidates and preserves the previous active snapshot on failure.

```mermaid
flowchart LR
 S["Versioned source batch"] --> R["Raw immutable evidence"] --> B["Bronze ingestion metadata"] --> SI["Silver typed + deduplicated"] --> G["Gold analytics-ready"] --> P["Serving snapshot"]
 B -. "quality failure" .-> KEEP["Keep prior active snapshot"]
 SI -. "quality failure" .-> KEEP
 G -. "quality failure" .-> KEEP
```

## 4. Python and PySpark parity

Two physical engines implement one logical contract and compare normalized outputs.

```mermaid
flowchart TD
 INPUT["Same source snapshot"] --> PY["Canonical Python engine"]
 INPUT --> SP["Optional PySpark engine"]
 PY --> PN["Normalized logical rows"]
 SP --> SN["Normalized logical rows"]
 PN --> CMP{"Schemas, counts, hashes, rejects, gates, lineage equal?"}
 SN --> CMP
 CMP --> REPORT["Machine-readable parity report"]
```

## 5. Airflow DAG

Airflow coordinates existing stage functions; it contains no transformation or policy logic.

```mermaid
flowchart LR
 START --> SOURCE["Generate source"] --> WAIT["Source sensor"] --> RAW --> B["Bronze"] --> BG["Bronze gate"] --> S["Silver"] --> SG["Silver gate"] --> G["Gold"] --> GG["Gold gate"] --> PUB["Publish"] --> VERIFY["Verify"] --> SUCCESS
```

## 6. Serving backend abstraction

One validated-query contract supports default SQLite and optional PostgreSQL without moving authorization into a driver.

```mermaid
flowchart TD
 VALID["Validated SQL"] --> QB["QueryBackend contract"]
 QB --> SQ["SQLite read-only backend"]
 QB --> PG["Optional PostgreSQL backend"]
 SQ --> N["Normalized result + provenance"]
 PG --> N
```

## 7. Audit and lineage

An answer resolves through immutable platform metadata back to its source batch.

```mermaid
flowchart LR
 A["Answer"] --> AU["Audit run"] --> SERVE["Serving snapshot"] --> GOLD --> SILVER --> BRONZE --> RAW --> BATCH["Source batch"]
 SERVE -.-> ORCH["Optional Airflow run"]
 GOLD -.-> APP["Optional Spark application"]
```

## 8. Kubernetes topology

Kubernetes deploys the existing services with internal networking and persistent claims.

```mermaid
flowchart TD
 ING["Optional Ingress"] --> UIS["UI ClusterIP"] --> UI["Streamlit Deployment"]
 ING --> APIS["API ClusterIP"] --> API["FastAPI Deployment"]
 ING --> AWS["Airflow ClusterIP"] --> AW["Airflow webserver"]
 AS["Airflow scheduler"] --> LAKE["Lake PVC"]
 AS --> PG["PostgreSQL StatefulSet"]
 SP["Suspended Spark Job"] --> LAKE
```

## 9. Verification boundary

Green local paths executed; optional external runtimes stop at contract or static validation in this environment.

```mermaid
flowchart LR
 LIVE["Live: Python + SQLite + API + UI + local lake"] --> TESTED["Contract-tested: PostgreSQL + Spark + Airflow"] --> STATIC["Statically validated: Kubernetes + Compose"] --> PENDING["Pending environment-specific live runs"]
```

## 10. Project evolution

Each milestone established contracts before adding a larger runtime.

```mermaid
timeline
 title Contract-first platform evolution
 section Analytics
 Bounded SQL analyst : privacy : validation : audit
 section Data
 Versioned datasets : snapshots : raw/bronze/silver/gold
 section Scale
 PostgreSQL boundary : optional PySpark parity
 section Operations
 Optional Airflow : Kubernetes manifests
 section Portfolio
 One-command demo : guided walkthrough : release package
```

