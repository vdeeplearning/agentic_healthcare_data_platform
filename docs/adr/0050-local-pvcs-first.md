# ADR 0050: Use generic local PVC contracts first
## Context
The lake, platform metadata, audit database, Airflow logs, and PostgreSQL data require persistence.
## Problem
Hardcoding host paths or a cloud storage class would make the baseline unsafe or non-portable.
## Alternatives considered
`hostPath`, ephemeral volumes, cloud volumes, external object storage, and storage-class-neutral PVCs were considered.
## Decision
Declare generic PVCs without `storageClassName`. Use `ReadWriteOnce` and one replica where local-file semantics require it.
## Consequences
The cluster's default provisioner chooses storage and data survives pod recreation.
## Tradeoffs
The baseline does not promise multi-node `ReadWriteMany`, cross-zone replication, snapshots, encryption, or backups.
## Future implications
Scaling stateful consumers requires an external database/object store or a proven RWX implementation without changing logical data contracts.

