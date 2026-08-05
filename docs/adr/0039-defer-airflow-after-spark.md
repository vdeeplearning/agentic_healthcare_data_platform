# ADR 0039: Defer Airflow until Spark jobs are established
## Context
Python and Spark transformations now have explicit commands and metadata.
## Problem
Adding scheduling while execution parity is new would mix semantic and operational failures.
## Alternatives considered
Add DAGs now, use cron, or defer orchestration.
## Decision
Defer Airflow; it will later call registered engine commands and record orchestration IDs.
## Consequences
Current execution remains explicit and developer-controlled.
## Tradeoffs
Retries and schedules are manual.
## Future implications
The next milestone should orchestrate these exact contracts without embedding policy in DAGs.
