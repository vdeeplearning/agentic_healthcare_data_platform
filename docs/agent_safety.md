# Agent safety and authorization

The analyst is a constrained compiler, not a direct model-to-database bridge.

1. Normalize and classify the request.
2. Deny high-risk row-level export requests or request clarification for ambiguity.
3. Create a typed `AnalysisPlan`.
4. Select a deterministic template or accept one structured model proposal.
5. Parse SQL into an AST and validate tables, columns, functions, joins, complexity, and limits.
6. Execute only through a read-only backend with timeout and row bounds.
7. Apply privacy and result checks.
8. Compose an answer from verified result fields and persist the audit record.

Small-cell suppression uses a default minimum group size of 10. Statistical execution is limited to registered tools. Model self-critique cannot override deterministic controls. See [safeguards](safeguards.md) and [relationship policy](relationship_policy.md).

