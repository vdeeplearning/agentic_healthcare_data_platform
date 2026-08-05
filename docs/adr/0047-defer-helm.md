# ADR 0047: Defer Helm packaging
## Context
The first Kubernetes milestone needs inspectable, provider-neutral deployment resources.
## Problem
Templating too early can obscure defaults and multiply unsupported configuration combinations.
## Alternatives considered
Helm, Kustomize overlays, generated YAML, and plain manifests were considered.
## Decision
Commit plain Kubernetes YAML plus a native Kustomization resource list. Do not add Helm charts in this milestone.
## Consequences
Every deployed field is directly reviewable and client-side rendering needs only `kubectl`.
## Tradeoffs
Operators must edit or patch image tags, storage, hosts, and environment-specific values themselves.
## Future implications
A future Helm chart may package these same resources after multiple real environments establish stable values and upgrade behavior.

