from scripts.validate_docs import validate_docs
from pathlib import Path
import yaml


def test_documentation_links_and_diagrams_are_valid():
    assert validate_docs() == []


def test_github_actions_workflow_parses_and_runs_release_gates():
    workflow_path=Path(__file__).resolve().parents[1]/".github"/"workflows"/"ci.yml"
    workflow=yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps=workflow["jobs"]["test"]["steps"]
    commands="\n".join(str(step.get("run","")) for step in steps)
    assert "validate_docs.py" in commands
    assert "scripts.demo --smoke" in commands
    assert "pytest --cov=src" in commands
