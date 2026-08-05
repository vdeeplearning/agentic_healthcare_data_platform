# Version 1.0.0 release notes

## Summary

Version 1.0.0 marks the stable portfolio release of the Agentic Healthcare Data Platform. The release combines governed AI-assisted SQL analytics, a versioned lakehouse, optional distributed processing and orchestration, deployment manifests, and an auditable end-to-end demo over synthetic data.

## Architecture

The model proposes typed analytical intent and SQL. Deterministic software authorizes privacy, SQL structure, schema access, registered analytics, bounded execution, result plausibility, and evidence grounding. Data moves through raw, bronze, silver, and gold before serving. Python is canonical; optional Spark matches its logical contract; Airflow coordinates stages; Kubernetes deploys existing services.

## Run

- Windows: `./scripts/demo.ps1`
- macOS/Linux: `./scripts/demo.sh`
- CI smoke: `python -m scripts.demo --smoke`

## Verification

The local release gate reports 175 passed, 17 optional-runtime skips, and 92.87% source coverage against the 92% requirement. Python, SQLite, FastAPI, Streamlit, the local lake, audit, lineage, benchmark, and smoke demo are executable. PostgreSQL, Java/PySpark, native Airflow, Docker containers, and live Kubernetes remain environment-dependent and are not represented as locally executed. The tagged commit's GitHub Actions run remains the authority for remote CI status.

## Media

See the [screenshot inventory](demo.md#screenshot-inventory) and [video package](video_demo.md). Add the published video URL here after recording.

## Known limitations

Synthetic data only; no PHI certification. Local storage is not multi-node production state. Optional external runtimes require their own live integration environments. No Helm, cloud infrastructure, service mesh, or observability stack is included.

## Roadmap

Next: run the release commit through GitHub Actions, live-test optional runtimes in dedicated environments, publish immutable container images, record the prepared video, and add production identity, secrets, storage, monitoring, and recovery controls.
