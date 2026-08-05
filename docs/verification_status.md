# Verification status

## Meaning of terms

- **Implemented:** production-shaped code or manifests exist.
- **Contract-tested:** deterministic tests validate interfaces and behavior without the external runtime.
- **Statically validated:** configuration parses or renders but was not started.
- **Live-executed:** the real runtime completed locally.

## Current boundary

Python, SQLite, FastAPI, Streamlit, local lake processing, audit, lineage, benchmark, and demo smoke paths are live-executed. PostgreSQL has unit and shared contract coverage but no live DSN. PySpark has engine/parity contracts but no Java/PySpark runtime. Airflow has DAG and coordinator tests but no native scheduler runtime. Kubernetes YAML parses and Kustomize renders but no cluster is configured. Compose renders but the Docker daemon is stopped.

The CI badge in the README is the source of truth for the latest remote GitHub Actions result. Local verification results are recorded in release notes only after the complete suite finishes.

