# Audit and lineage

Every analysis has a bounded audit record containing the question, plan, validated SQL, status, timing, row count, approved statistics, warnings, answer, and snapshot provenance. Secrets and hidden model reasoning are never stored.

When the demo pipeline publishes serving data, lineage resolves:

`answer → audit run → serving snapshot → gold → silver → bronze → raw snapshot → source batch`

Airflow run metadata and Spark application metadata are additive operational provenance. Kubernetes deployment details do not alter analytical lineage. Failed candidates remain inactive, so active lineage continues to point to validated data.

