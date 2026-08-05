# Optional PySpark engine

`PySparkTransformationEngine` implements the same raw → bronze → silver → gold contracts as canonical Python. Explicit schemas prevent inference drift. Spark writes Parquet candidates plus canonical logical sidecars; parity compares normalized rows, schemas, counts, rejected records, warnings, checksums, validation, dataset identity, and lineage while allowing physical partition differences.

Install with `pip install -e ".[spark,dev]"` and use Java 17. The current verification environment lacks Java and PySpark, so real Spark execution is pending. Runtime-independent tests exercise engine selection, orchestration, failure behavior, and parity contracts without claiming a Spark cluster ran.

The LLM cannot submit Spark code, SQL expressions, UDFs, JARs, or quality policy. See ADRs 0030–0038.

