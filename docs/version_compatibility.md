# Version compatibility rules

| Change | Classification | Regenerate logical records? | Rematerialize snapshot? |
|---|---|---:|---:|
| Add optional manifest metadata | Backward-compatible additive | No | No |
| Change logical field meaning or remove a field | Incompatible logical schema | Yes | Yes |
| Refactor loader with identical output | Loader-only implementation | No | Policy-dependent |
| Change loader major version or materialization format | Materialization incompatibility | No | Yes |
| Add/rebuild an analytical index | Analytical physical change | No | Yes, if snapshot identity/governance requires it |
| Add a compatible analytical view | Analytical schema/view change | No | Usually yes |
| Change a governed metric definition | Metric governance change | Usually no | Recompute affected gold/serving outputs |
| Change generator formula or RNG ordering | Generator change | Yes | Yes |
| Change seed or major generation parameter | New logical dataset | Yes | Yes |

Generator and logical-schema major versions must match the supported major. Loader major versions must match before materialization. Manifest and snapshot repository schemas use exact numbered migrations and reject unknown future versions. Audit schema changes are additive and old rows remain readable.
