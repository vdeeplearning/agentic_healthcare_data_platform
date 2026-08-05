# Versioned data lake

The local lake implements four governed layers:

- **Raw:** immutable source-shaped evidence.
- **Bronze:** ingestion metadata and structural checks.
- **Silver:** typing, cleanup, deduplication, domain checks, and referential validation.
- **Gold:** analytics-ready entities and registered metric compatibility.

Each layer has manifests, checksums, validation results, parent snapshots, and atomic candidate publication. Failed candidates do not replace the active validated snapshot. The default filesystem implementation is transparent and deterministic; it is not represented as cloud object storage or a distributed transaction system.

Use `python -m src.lake.cli --help` for explicit lifecycle commands. See ADRs 0020–0027.

