# Kubernetes deployment

Plain Kubernetes YAML under `kubernetes/` deploys the existing API, UI, PostgreSQL, Airflow scheduler/webserver, and optional suspended Spark Job. It provides namespaces, ClusterIP Services, generic PVCs, ConfigMaps, a template Secret, probes, resource bounds, graceful termination, disruption policy, and an optional Ingress example.

Kubernetes is deployment-only. It does not define analytics, transformations, safety, lineage, or API behavior. Kustomize rendering and deterministic YAML validation pass; no Kubernetes API server, kind, or minikube was available for a live deployment.

The manifests intentionally omit Helm, cloud-provider resources, Istio/service mesh, Argo, Terraform, and observability stacks. See ADRs 0046–0051 and run `python scripts/validate_kubernetes.py`.

