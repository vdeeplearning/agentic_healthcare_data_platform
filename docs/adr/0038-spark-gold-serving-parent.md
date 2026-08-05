# ADR 0038: Spark gold is a serving-snapshot parent
## Context
Serving lineage already points to a gold snapshot.
## Problem
Engine origin could be lost when Spark gold loads into SQLite or PostgreSQL.
## Alternatives considered
Store only source batch, add engine to audit text, or retain the exact gold parent.
## Decision
Spark gold metadata and snapshot ID flow through the existing serving publication boundary.
## Consequences
Analysis lineage identifies Spark application metadata and raw ancestry.
## Tradeoffs
Serving publication depends on canonical logical sidecars.
## Future implications
Cluster job IDs can populate the existing optional runtime metadata.
