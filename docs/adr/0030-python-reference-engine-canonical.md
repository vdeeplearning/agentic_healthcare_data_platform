# ADR 0030: Python reference engine remains canonical
## Context
The local Python lake implementation already defines verified transformation semantics.
## Problem
Adding Spark could accidentally let distributed mechanics redefine policy.
## Alternatives considered
Replace Python, maintain unrelated implementations, or keep Python as the compatibility oracle.
## Decision
Python remains the default and canonical reference; Spark must prove logical parity.
## Consequences
Small deterministic tests remain Java-free and fast.
## Tradeoffs
Two implementations require ongoing parity governance.
## Future implications
Every future engine must compare against the Python reference before publication authority expands.
