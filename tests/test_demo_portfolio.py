from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from scripts.demo import build_demo, reset_demo
from src.config import get_settings

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_demo_smoke_builds_verified_sqlite_pipeline(tmp_path):
    serving, summary = build_demo(tmp_path / "portfolio", "test")
    assert serving.exists()
    assert summary.patient_count == 300
    assert summary.run.status == "completed"
    assert set(summary.run.layer_snapshot_ids) == {"raw", "bronze", "silver", "gold"}


def test_reset_refuses_unrelated_paths(tmp_path):
    with pytest.raises(ValueError, match="Refusing"):
        reset_demo(tmp_path / "unrelated")


def test_portfolio_mode_adds_guided_walkthrough(monkeypatch):
    monkeypatch.setenv("CLINICAL_SQL_PORTFOLIO_MODE", "true")
    get_settings.cache_clear()
    page = AppTest.from_file(APP_PATH, default_timeout=30).run()
    get_settings.cache_clear()
    assert not page.exception
    assert any("Portfolio walkthrough" in item.value for item in page.success)
    assert any(button.label == "Question 1" for button in page.button)
    assert any(metric.label == "Transformation engine" for metric in page.metric)
