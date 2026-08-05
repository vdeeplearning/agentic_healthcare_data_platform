# ADR 0033: Parquet for Spark bronze, silver, and gold
## Context
Spark naturally reads and writes partitioned columnar data.
## Problem
JSON Lines does not demonstrate realistic Spark physical output.
## Alternatives considered
Keep JSONL, add a lakehouse format, or use plain Parquet.
## Decision
Spark writes Parquet directories while retaining canonical logical JSONL sidecars for identity and serving compatibility.
## Consequences
Physical output is realistic and logical comparison remains stable.
## Tradeoffs
Sidecars duplicate a compact canonical representation.
## Future implications
Object storage can retain Parquet parts and a logical checksum manifest; no Delta, Iceberg, or Hudi dependency is implied.
