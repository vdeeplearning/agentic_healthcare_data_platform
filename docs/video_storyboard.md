# Video storyboard

| Time | Screen | Action | Expected state | Backup |
|---|---|---|---|---|
| 0:00–0:20 | Title + executive diagram | Point to question and authorization boundary | Project title and synthetic-data label visible | `executive-dashboard.png` |
| 0:20–0:50 | Architecture | Trace question → validator → serving and lake → serving | Mermaid diagram rendered | Architecture page still |
| 0:50–1:20 | Medallion diagram | Trace raw → bronze → silver → gold; mention Python/Spark parity | Pipeline and parity diagrams visible | `medallion-pipeline.png` |
| 1:20–1:45 | Airflow diagram | Trace gates and publication | DAG diagram visible | `airflow-dag.png` |
| 1:45–2:45 | Streamlit | Click Question 1, Analyze, Plan + SQL, answer/chart | Completed result, validated SQL, chart | Pre-captured result stills |
| 2:45–3:30 | Safety | Show Safety checks; run export request; mention small cells/tools | Validation passes and denial appears | Safety still |
| 3:30–4:15 | Audit + lineage | Open Audit trace then Lineage | Audit ID and lake ancestry visible | Audit/lineage stills |
| 4:15–4:45 | Capability matrix | Highlight implementation and verification columns | Accurate status table visible | README still |
| 4:45–5:00 | Closing title | Point to repository and central principle | URL and principle visible | Static closing card |

