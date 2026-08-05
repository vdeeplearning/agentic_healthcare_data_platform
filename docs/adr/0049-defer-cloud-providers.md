# ADR 0049: Defer cloud-provider integrations
## Context
The platform must remain runnable without a cloud account.
## Problem
Managed databases, object stores, ingress controllers, identity systems, and provider-specific volume classes would couple deployment to one vendor.
## Alternatives considered
AWS, Azure, GCP, and provider-neutral Kubernetes resources were considered.
## Decision
Use generic PVCs, ClusterIP Services, template Secrets, and an optional standards-based Ingress. Add no cloud SDK, managed-service resource, or provider annotation.
## Consequences
Manifests remain portable but do not provision external infrastructure.
## Tradeoffs
Production operators must supply storage classes, DNS, TLS, identity, backup, and managed services outside this repository.
## Future implications
Provider overlays require separate ADRs and must preserve application contracts and lineage identities.

