"""Deterministic structural validation for the repository's Kubernetes YAML."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
KUBERNETES = ROOT / "kubernetes"
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "Job"}
LONG_RUNNING_KINDS = {"Deployment", "StatefulSet"}
PLACEHOLDER = re.compile(r"REPLACE|CHANGEME|YOUR[_-]", re.IGNORECASE)


def documents() -> list[tuple[Path, dict[str, Any]]]:
    result: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(KUBERNETES.glob("*.yaml")):
        for document in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if document:
                result.append((path, document))
    return result


def _containers(document: dict[str, Any]) -> Iterable[dict[str, Any]]:
    template = document["spec"].get("template", {})
    pod_spec = template.get("spec", {})
    yield from pod_spec.get("initContainers", [])
    yield from pod_spec.get("containers", [])


def validate() -> list[str]:
    errors: list[str] = []
    loaded = documents()
    identities: set[tuple[str, str, str]] = set()
    names = {(doc.get("kind"), doc.get("metadata", {}).get("name")) for _, doc in loaded}

    for path, doc in loaded:
        kind = doc.get("kind")
        metadata = doc.get("metadata", {})
        name = metadata.get("name")
        label = f"{path.name}:{kind}/{name}"
        if not doc.get("apiVersion") or not kind or (not name and kind != "Kustomization"):
            errors.append(f"{path.name}: apiVersion, kind, and metadata.name are required")
            continue
        namespace = metadata.get("namespace", "")
        identity = (kind, namespace, name)
        if identity in identities:
            errors.append(f"{label}: duplicate resource identity")
        identities.add(identity)
        if kind != "Namespace" and kind != "Kustomization" and namespace != "agentic-healthcare":
            errors.append(f"{label}: resource must use the agentic-healthcare namespace")

        if kind == "Service":
            service_type = doc.get("spec", {}).get("type", "ClusterIP")
            if service_type != "ClusterIP":
                errors.append(f"{label}: only ClusterIP services are allowed")
        if kind == "PersistentVolumeClaim":
            request = doc.get("spec", {}).get("resources", {}).get("requests", {}).get("storage")
            if not request:
                errors.append(f"{label}: storage request is required")
            if "storageClassName" in doc.get("spec", {}):
                errors.append(f"{label}: storageClassName must remain cluster-neutral")

        if kind in WORKLOAD_KINDS:
            pod_spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            if not pod_spec.get("terminationGracePeriodSeconds"):
                errors.append(f"{label}: terminationGracePeriodSeconds is required")
            if kind == "Job" and pod_spec.get("restartPolicy") not in {"Never", "OnFailure"}:
                errors.append(f"{label}: Job restartPolicy must be Never or OnFailure")
            for container in _containers(doc):
                container_label = f"{label}:{container.get('name')}"
                image = container.get("image", "")
                if not image or image.endswith(":latest") or ":" not in image:
                    errors.append(f"{container_label}: image must use an explicit non-latest tag")
                if container.get("imagePullPolicy") not in {"IfNotPresent", "Always", "Never"}:
                    errors.append(f"{container_label}: imagePullPolicy is required")
                if container in pod_spec.get("containers", []):
                    resources = container.get("resources", {})
                    if not resources.get("requests") or not resources.get("limits"):
                        errors.append(f"{container_label}: resource requests and limits are required")
                    if kind in LONG_RUNNING_KINDS:
                        for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
                            if probe not in container:
                                errors.append(f"{container_label}: {probe} is required")
                for source in container.get("envFrom", []):
                    config_name = source.get("configMapRef", {}).get("name")
                    secret_name = source.get("secretRef", {}).get("name")
                    if config_name and ("ConfigMap", config_name) not in names:
                        errors.append(f"{container_label}: unknown ConfigMap {config_name}")
                    if secret_name and ("Secret", secret_name) not in names:
                        errors.append(f"{container_label}: unknown Secret {secret_name}")

    template_path = KUBERNETES / "secret.template.yaml"
    template_docs = list(yaml.safe_load_all(template_path.read_text(encoding="utf-8")))
    if len(template_docs) != 1 or template_docs[0].get("kind") != "Secret":
        errors.append("secret.template.yaml must contain exactly one Secret")
    else:
        values = template_docs[0].get("stringData", {})
        for key in ("POSTGRES_PASSWORD", "AIRFLOW__CORE__FERNET_KEY", "AIRFLOW__WEBSERVER__SECRET_KEY"):
            if key not in values or not PLACEHOLDER.search(str(values[key])):
                errors.append(f"secret.template.yaml:{key} must remain a placeholder")

    kustomization = yaml.safe_load((KUBERNETES / "kustomization.yaml").read_text(encoding="utf-8"))
    for resource in kustomization.get("resources", []):
        if not (KUBERNETES / resource).is_file():
            errors.append(f"kustomization.yaml: missing resource {resource}")
    if "secret.template.yaml" in kustomization.get("resources", []):
        errors.append("kustomization.yaml must not apply the placeholder Secret")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Validated {len(documents())} Kubernetes YAML documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
