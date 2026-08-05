# Portfolio demo and screenshot guide

## Run the demo

Windows: `./scripts/demo.ps1`

macOS/Linux: `./scripts/demo.sh`

The launcher installs the base project into `.venv`, runs canonical Python through raw/bronze/silver/gold, publishes SQLite, verifies a deterministic query, launches FastAPI and Streamlit, and prints URLs. Press Ctrl+C for clean shutdown. Reset scripts delete only `data/demo`.

## Suggested walkthrough

1. Start on the executive workspace and point out “Synthetic only,” Python, and SQLite.
2. Select the encounter-volume curated question and click Analyze.
3. Show the grounded answer and chart.
4. Open Plan + SQL and explain typed intent plus AST validation.
5. Open Safety checks and Audit trace.
6. Open Lineage and trace serving → gold → silver → bronze → raw.
7. Run the patient-export question to demonstrate denial.

## Screenshot inventory

Store sanitized PNG files in `docs/images/`:

1. `executive-dashboard.png`
2. `typed-plan-validated-sql.png`
3. `answer-and-chart.png`
4. `safety-validation-trace.png`
5. `audit-record.png`
6. `end-to-end-lineage.png`
7. `medallion-pipeline.svg`
8. `airflow-dag.svg`
9. `kubernetes-topology.svg`
10. `verification-matrix.svg`

## Capture checklist

- Use 1440×900 or 1920×1080 at 100% browser zoom.
- Crop browser chrome and unrelated desktop content.
- Confirm no API key, DSN, local absolute path, email, secret, or personal notification is visible.
- Use only the generated synthetic dataset.
- Keep question, answer, SQL, and chart text legible.
- Add descriptive Markdown alt text wherever each image is embedded.
- Capture the exact verified screen; do not composite or fabricate results.

## Short GIF or MP4 preview

Record 20–40 seconds at 1280×720: click Question 1, Analyze, Plan + SQL, the answer/chart, then Lineage. Crop to the Streamlit content region, remove idle time, use 8–12 fps for GIF or H.264 for a smaller silent MP4, and avoid showing the address bar. A manual capture is preferred over adding a heavy media dependency.
