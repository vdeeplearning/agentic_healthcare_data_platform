from scripts.validate_kubernetes import KUBERNETES, documents, validate


def test_kubernetes_manifests_are_structurally_valid():
    assert validate() == []


def test_required_component_manifests_exist():
    expected = {
        "namespace.yaml", "configmap.yaml", "secret.template.yaml", "storage.yaml",
        "postgres.yaml", "api.yaml", "ui.yaml", "airflow-scheduler.yaml",
        "airflow-webserver.yaml", "spark-job.yaml", "ingress.example.yaml",
        "kustomization.yaml",
    }
    assert expected <= {path.name for path in KUBERNETES.glob("*.yaml")}


def test_secret_template_is_not_applied_by_kustomize():
    text = (KUBERNETES / "kustomization.yaml").read_text(encoding="utf-8")
    assert "secret.template.yaml" not in text


def test_every_yaml_file_parses_to_at_least_one_document():
    parsed_paths = {path for path, _ in documents()}
    assert parsed_paths == set(KUBERNETES.glob("*.yaml"))

