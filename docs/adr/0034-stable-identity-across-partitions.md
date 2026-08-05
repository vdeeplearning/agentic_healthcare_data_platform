# ADR 0034: Stable logical identity across partitioned output
## Context
Spark part names and partition placement can change between equivalent runs.
## Problem
Hashing physical paths would make incidental layout semantic.
## Alternatives considered
Hash directories, force one part, or hash canonical logical rows and schemas.
## Decision
Object identity uses sorted canonical logical content, entity, transformation version, engine, and format—not part names.
## Consequences
Equivalent Spark layouts compare equal logically while Spark snapshots remain implementation-specific.
## Tradeoffs
Canonicalization adds driver work and is intended as a correctness foundation, not the final large-scale hashing strategy.
## Future implications
Distributed aggregate record hashes can replace driver collection while preserving identity semantics.
