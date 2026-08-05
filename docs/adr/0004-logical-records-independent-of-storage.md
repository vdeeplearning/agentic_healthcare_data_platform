# ADR 0004: Separate logical synthetic records from storage

- Status: Accepted
- Date: 2026-08-05

## Context

The original generator calculated fictional healthcare facts and inserted SQLite tuples in one function. Future SQLite, PostgreSQL, raw-file, Parquet, and Spark targets must receive the same facts.

## Problem

Duplicating formulas in each writer would cause seed drift, inconsistent metrics, and provenance that could not identify which logical dataset was loaded.

## Alternatives considered

- Keep one SQLite generator and export from SQLite later. Simple, but makes SQLite an accidental source format and hides generation provenance.
- Build one in-memory object graph. Clear, but the full fixture would consume unnecessary memory.
- Emit typed batches from one generator. Slightly more structure, but portable and bounded.

## Decision

Use typed `NamedTuple` domain records and a versioned `SyntheticRecordGenerator` that emits entity batches. Preserve formulas, random-number ordering, deliberate anomalies, and fixture sizes.

## Consequences

Storage writers share one logical input. The generator retains small lookup state and inpatient eligibility state, but does not retain the full encounter dataset.

## Tradeoffs

Entity ordering and foreign-key dependencies become part of the generator/loader contract. Named tuples favor efficient bulk loading over rich domain behavior.

## Future implications

Raw JSON/CSV, Parquet, PostgreSQL, and Spark writers can consume these batches without moving policy or AI authority into generation.

