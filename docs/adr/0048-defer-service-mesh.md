# ADR 0048: Defer service mesh
## Context
Kubernetes Services already provide the internal discovery required by this deployment.
## Problem
Istio or another mesh would add proxies, certificates, traffic policy, telemetry, and failure modes unrelated to analytical correctness.
## Alternatives considered
Istio, another service mesh, application-managed networking, and ordinary ClusterIP Services were considered.
## Decision
Use standard Kubernetes Services and an optional Ingress example. Do not add a service mesh.
## Consequences
Networking remains understandable and no sidecars intercept clinical analytics traffic.
## Tradeoffs
Mutual TLS, advanced traffic splitting, and mesh telemetry are not provided.
## Future implications
A mesh requires a separate threat model, performance evidence, certificate ownership, and operational runbook.

