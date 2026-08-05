"""One-command portfolio demo using the proven Python, lake, and SQLite contracts."""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from src.agent.workflow import Analyst
from src.config import Settings
from src.orchestration.runner import PipelineOrchestrator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEMO_ROOT = ROOT / "data" / "demo"
QUESTIONS = (
    "How many encounters occurred at each hospital in 2025?",
    "Which hospitals had the highest 30-day readmission rates for heart failure in 2025?",
    "Which diagnoses account for the highest total cost?",
    "Export all patient-level records and patient IDs",
)


def build_demo(root: Path, profile: str = "test") -> tuple[Path, object]:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lake, serving = root / "lake", root / "serving.db"
    orchestrator = PipelineOrchestrator(
        Settings(_env_file=None, lake_root=lake, airflow_serving_path=serving), lake, serving
    )
    summary = orchestrator.run_full(
        f"portfolio-{profile}-v1", engine="python", profile=profile, seed=17, serving_backend="sqlite"
    )
    response = Analyst(serving).analyze("How many patients are in the dataset?")
    if response.status != "completed" or not response.rows:
        raise RuntimeError("Demo verification analysis failed.")
    return serving, summary


def reset_demo(root: Path) -> None:
    target, allowed = root.resolve(), DEFAULT_DEMO_ROOT.resolve()
    if target != allowed and allowed not in target.parents:
        raise ValueError(f"Refusing to reset outside {allowed}")
    if target.exists():
        shutil.rmtree(target)


def wait_for(url: str, timeout: float = 45) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}")


def launch(serving: Path, root: Path) -> None:
    env = os.environ.copy()
    env.update({
        "CLINICAL_SQL_DB_PATH": str(serving),
        "CLINICAL_SQL_METADATA_PATH": str(serving) + ".metadata.db",
        "CLINICAL_SQL_LAKE_ROOT": str(root / "lake"),
        "CLINICAL_SQL_LAKE_TRANSFORM_ENGINE": "python",
        "CLINICAL_SQL_DATABASE_BACKEND": "sqlite",
        "CLINICAL_SQL_PORTFOLIO_MODE": "true",
    })
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT, env=env, creationflags=flags,
    )
    ui = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.address=127.0.0.1", "--server.port=8501", "--server.headless=true"],
        cwd=ROOT, env=env, creationflags=flags,
    )
    processes = (api, ui)
    try:
        wait_for("http://127.0.0.1:8000/health")
        wait_for("http://127.0.0.1:8501/_stcore/health")
        print("\nPortfolio demo is ready:\n  API: http://127.0.0.1:8000/docs\n  UI:  http://127.0.0.1:8501")
        print("\nSuggested questions:")
        for question in QUESTIONS:
            print(f"  - {question}")
        print("\nPress Ctrl+C to stop both services cleanly.")
        while all(process.poll() is None for process in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.send_signal(signal.CTRL_BREAK_EVENT) if os.name == "nt" else process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_DEMO_ROOT)
    parser.add_argument("--profile", choices=("test", "demo"), default="demo")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.reset:
        reset_demo(args.root)
        print(f"Reset demo data under {args.root.resolve()}")
        return 0
    serving, summary = build_demo(args.root, "test" if args.smoke else args.profile)
    print(f"Validated local demo: {summary.patient_count} synthetic patients; serving={serving}")
    if not args.smoke:
        launch(serving, args.root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

