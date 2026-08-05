# Optional Apache Airflow orchestration

The `clinical_lake_pipeline` DAG coordinates source generation, raw publication, three reviewed transformations, quality gates, serving publication, verification, and completion. Engine selection chooses canonical Python or optional Spark through the existing factory.

Airflow records run IDs, timing, retries, failures, snapshots, manifests, quality results, and parent lineage. It does not contain transformations, SQL policy, metrics, privacy rules, or interactive analysis.

The baseline uses LocalExecutor, bounded retries, catchup disabled by default, one active run, logging-only notifications, and a daily schedule example. Native Airflow is not installed in the current Windows runtime; the DAG and runtime-independent coordinator are implemented and tested, while scheduler/webserver execution remains pending. See ADRs 0041–0045.

