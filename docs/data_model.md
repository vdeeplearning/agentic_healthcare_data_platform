# Data model

The synthetic relational model separates patients, hospitals, providers, encounters, diagnoses, procedures, laboratory results, readmissions, and quality measures. Bridge tables represent encounter-to-diagnosis and encounter-to-procedure many-to-many relationships.

Logical records are storage-independent typed facts. Loaders map them into SQLite, PostgreSQL, JSON Lines, or Spark DataFrames without changing their meaning. Dataset identity describes stable generation inputs; a manifest describes logical contents; a snapshot identifies one physical materialization.

See [database schema](database_schema.md), SQL definitions under `sql/`, and ADRs 0004, 0005, 0010, and 0019.

