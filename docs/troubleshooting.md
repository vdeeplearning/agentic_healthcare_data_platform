# Troubleshooting

- **Demo installation fails:** confirm Python 3.11+, internet access for first dependency installation, and virtual-environment support.
- **Port 8000 or 8501 is occupied:** stop the conflicting process before rerunning the demo.
- **Demo reset is refused:** reset scripts intentionally delete only `data/demo`.
- **PostgreSQL tests skip:** configure a reachable `CLINICAL_SQL_TEST_POSTGRES_DSN`.
- **Spark capability fails:** install Java 17 and the `spark` optional dependency.
- **Airflow import skips:** install Airflow in a supported Linux/WSL/container environment.
- **PVCs stay pending:** configure a default Kubernetes storage provisioner.
- **Images do not pull:** build/publish the explicit tags or load them into the local cluster.
- **Question asks for patient rows:** high-risk export denial is expected behavior.

