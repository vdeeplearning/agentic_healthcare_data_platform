# Operations

Choose the smallest appropriate runtime:

- Local Python: fastest development and portfolio demo.
- Docker Compose: API/UI and optional PostgreSQL on one Docker host.
- Airflow: scheduled batch coordination using existing contracts.
- Kubernetes: deployment operations for independently packaged components.

Configuration comes from environment-backed `Settings`. Never commit `.env`, populated Kubernetes Secrets, API keys, DSNs, generated databases, lake objects, logs, or recordings containing local/private information. Backup, disaster recovery, TLS, identity, external secrets, and multi-node state remain production responsibilities.

