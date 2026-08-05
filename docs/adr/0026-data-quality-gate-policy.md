# ADR 0026: Deterministic data-quality gates
## Context
Validated serving data must not be replaced by malformed or inconsistent candidates.
## Problem
Logging errors without blocking activation creates false confidence.
## Alternatives considered
Warnings only, manual approval only, silent row dropping, and deterministic blocking gates were considered.
## Decision
Checksums, parsing, keys, domains, references, required entities, and rate bounds determine publication eligibility.
## Consequences
Rejected rows and warnings remain explicit; a failed run cannot activate.
## Tradeoffs
Conservative gates may require a reviewed rule change for legitimate new data.
## Future migration implications
Distributed checks must produce equivalent structured `ValidationResult` evidence.
