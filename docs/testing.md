# Testing and quality gates

The suite covers agent behavior, privacy denial, SQL validation, metrics, statistics, API, Streamlit reruns, database contracts, metadata migrations, snapshots, lake transformations, failed publication preservation, Python/Spark parity contracts, Airflow orchestration, Kubernetes manifests, and the portfolio demo.

```bash
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=92
python -m compileall -q src tests scripts dags
python -m src.cli benchmark --limit 5
python -m scripts.demo --smoke
python scripts/validate_kubernetes.py
```

Optional live tests skip honestly when PostgreSQL, Java/PySpark, or Airflow is unavailable. See [verification status](verification_status.md).

