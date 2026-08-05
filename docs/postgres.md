# Optional PostgreSQL serving

PostgreSQL implements the same query and loading boundaries as SQLite. The backend normalizes catalogs and results, enforces read-only execution and statement timeouts, and participates in shared backend contract tests. The loader registers serving snapshots and preserves gold parentage.

Use a dedicated schema and separate loader and query roles in real environments. Unit and contract tests run without a server; live integration and parity require `CLINICAL_SQL_TEST_POSTGRES_DSN`. No live DSN or working Docker daemon was available during current verification.

