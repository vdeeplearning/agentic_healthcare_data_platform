"""Streamlit portfolio UI."""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import streamlit as st
from src.agent.workflow import Analyst
from src.config import get_settings
from src.database.connection import connect_read_only,schema_catalog
from src.database.seed import generate_database
from src.demo.curated_questions import EXAMPLES
from src.metrics.registry import METRICS
from src.audit.repository import SQLiteAuditStore
from src.metadata.lineage import LineageResolver
from src.metadata.repository import SQLiteManifestStore,metadata_path_for
from src.lake.store import LocalFilesystemLakeStore

st.set_page_config(page_title="Agentic Clinical SQL Analyst",page_icon="🛡️",layout="wide")
settings=get_settings()
if not settings.db_path.exists():
    with st.spinner("Creating a compact deterministic demo database…"): generate_database(settings.db_path,settings.seed,2_500,10_000)
st.title("Agentic Clinical SQL Analyst")
st.info("Synthetic data only • Portfolio and education use • Not a clinical decision system")
st.caption("Natural language → typed plan → validated SQL AST → query-plan review → read-only execution → deterministic result checks → grounded answer")
if settings.portfolio_mode:
    st.success("Portfolio walkthrough: choose a curated question, inspect deterministic authorization, then trace the answer to its source batch.")
    status_columns=st.columns(3)
    status_columns[0].metric("Transformation engine",settings.lake_transform_engine.title())
    status_columns[1].metric("Serving backend",settings.database_backend.title())
    status_columns[2].metric("Data classification","Synthetic only")
with st.sidebar:
    st.header("Execution")
    st.subheader("OpenAI connection")
    st.caption("Paste a key to enable API-backed analysis. Leave it blank to use the free deterministic demo.")
    api_key=st.text_input(
        "OpenAI API key",
        type="password",
        key="openai_api_key",
        placeholder="sk-…",
        help="Kept only in this Streamlit browser session. It is not written to the database, audit log, or project files.",
    ).strip()
    if api_key:
        st.success("API-backed planning enabled for non-demo questions")
        if st.button("Clear API key", width="stretch"):
            st.session_state["openai_api_key"] = ""
            st.rerun()
    else:
        st.info("Deterministic demo mode — no API key required")
    with connect_read_only(settings.db_path) as c:
        counts={table:c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("patients","hospitals","providers","encounters")}
    st.metric("Synthetic encounters",f"{counts['encounters']:,}"); st.metric("Hospitals",counts["hospitals"])
st.subheader("Ask a question")
if settings.portfolio_mode:
    st.caption("Guided questions")
    question_columns=st.columns(3)
    for index,example in enumerate(EXAMPLES[:3]):
        if question_columns[index].button(f"Question {index+1}",help=example,width="stretch"):
            st.session_state["question_input"]=example
question=st.text_area("Healthcare analytics question",value=EXAMPLES[0],height=90,key="question_input")
history=st.session_state.setdefault("conversation_history",[])
if history:
    st.caption(f"Follow-up context enabled • {len(history)} previous turn(s)")
    if st.button("Clear conversation",width="content"):
        st.session_state["conversation_history"]=[]
        st.session_state.pop("last_result",None)
        st.rerun()
    with st.expander("Conversation history"):
        for turn_number,turn in enumerate(history,1):
            st.markdown(f"**You {turn_number}:** {turn['question']}")
            st.markdown(f"**Analyst:** {turn['answer']}")
with st.expander("Example questions"):
    for example in EXAMPLES: st.code(example,language=None)
if st.button("Analyze",type="primary",width="stretch"):
    context=[{
        "question":turn["question"],
        "grounded_answer":turn["answer"],
        "plan":turn.get("plan"),
        "validated_sql":turn.get("sql"),
        "verified_result_sample":turn.get("rows",[])[:10],
    } for turn in history[-5:]]
    metadata_path=settings.metadata_path or metadata_path_for(settings.db_path)
    snapshot=None
    if metadata_path.exists():
        try: snapshot=SQLiteManifestStore(metadata_path).get_active_snapshot("sqlite",settings.db_path.name)
        except Exception: snapshot=None
    result=Analyst(settings.db_path,settings.max_rows,settings.query_timeout_seconds,settings.small_cell_threshold,dataset_snapshot=snapshot).analyze(question,api_key or None,context)
    st.session_state["last_result"]=result
    history.append({"question":question,"answer":result.answer,"plan":result.plan.model_dump() if result.plan else None,"sql":result.sql,"rows":result.rows[:10],"status":result.status})
    st.session_state["conversation_history"]=history[-10:]
result=st.session_state.get("last_result")
if result:
    if result.status=="clarification_required": st.warning(result.clarification_question)
    elif result.status=="denied": st.error(result.answer)
    else: st.success(result.answer)
    if result.rows:
        frame=pd.DataFrame(result.rows); st.dataframe(frame,width="stretch",hide_index=True)
        numeric=[c for c in frame.columns if pd.api.types.is_numeric_dtype(frame[c])]
        labels=[c for c in frame.columns if c not in numeric]
        if labels and numeric: st.plotly_chart(px.bar(frame.head(20),x=labels[0],y=numeric[-1]),width="stretch")
    tabs=st.tabs(["Metric","Plan + SQL","Safety checks","Audit trace","Provenance","Lineage"])
    with tabs[0]: st.json(result.metric_definition or {})
    with tabs[1]: st.json(result.plan.model_dump(mode="json") if result.plan else {}); st.code(result.sql or "No SQL generated",language="sql")
    with tabs[2]: st.json(result.validation.model_dump() if result.validation else {}); [st.warning(w) for w in result.warnings]
    with tabs[3]: st.dataframe(pd.DataFrame([e.model_dump() for e in result.trace]),hide_index=True,width="stretch"); st.caption(f"Audit run ID: {result.run_id}")
    with tabs[4]: st.json(result.provenance)
    with tabs[5]:
        metadata_path=settings.metadata_path or metadata_path_for(settings.db_path)
        try:
            lineage=LineageResolver(SQLiteAuditStore(settings.db_path),SQLiteManifestStore(metadata_path),LocalFilesystemLakeStore(settings.lake_root)).resolve_run(result.run_id)
            st.json(lineage or {"status":"No snapshot lineage is attached to this run."})
        except Exception as exc: st.info(f"Lineage is unavailable for this local run: {type(exc).__name__}")
guide_tab,schema_tab,registry_tab=st.tabs(["Dataset Guide","Schema Explorer","Metric Registry"])
with guide_tab:
    st.subheader("What this synthetic dataset contains")
    st.markdown(
        "The database models a fictional healthcare delivery network for learning SQL and safe analytics. "
        "Its central fact table is **encounters**, connected to synthetic patients, hospitals, providers, "
        "diagnoses, procedures, laboratory results, readmission assessments, and quarterly quality measures."
    )
    with connect_read_only(settings.db_path) as connection:
        guide_tables=("patients","hospitals","providers","encounters","diagnoses","encounter_diagnoses","procedures","encounter_procedures","lab_results","readmissions","quality_measures")
        guide_counts={table:connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in guide_tables}
        date_bounds=connection.execute("SELECT MIN(admission_date),MAX(admission_date) FROM encounters").fetchone()
    overview_columns=st.columns(4)
    overview_columns[0].metric("Patients",f"{guide_counts['patients']:,}")
    overview_columns[1].metric("Hospitals",f"{guide_counts['hospitals']:,}")
    overview_columns[2].metric("Providers",f"{guide_counts['providers']:,}")
    overview_columns[3].metric("Encounters",f"{guide_counts['encounters']:,}")
    st.caption(f"Encounter dates: {date_bounds[0]} through {date_bounds[1]} • Deterministic synthetic seed: {settings.seed}")
    domains=pd.DataFrame([
        {"Domain":"People and facilities","Tables":"patients, hospitals, providers","Includes":"Demographics, insurance, region, hospital characteristics, specialties, and experience"},
        {"Domain":"Care delivery","Tables":"encounters","Includes":"Encounter type, admission/discharge dates, disposition, cost, mortality, and complications"},
        {"Domain":"Clinical coding","Tables":"diagnoses, encounter_diagnoses","Includes":"Diagnosis codes, categories, rank, and primary-diagnosis indicators"},
        {"Domain":"Procedures","Tables":"procedures, encounter_procedures","Includes":"Procedure vocabulary, category, and procedure date"},
        {"Domain":"Laboratory data","Tables":"lab_results","Includes":"Test name, value, unit, reference range, and collection time"},
        {"Domain":"Outcomes and quality","Tables":"readmissions, quality_measures","Includes":"30-day readmissions and quarterly hospital numerators, denominators, and rates"},
    ])
    st.dataframe(domains,hide_index=True,width="stretch")
    st.markdown("**Core relationships**")
    st.code("patients → encounters ← hospitals ← providers\nencounters → diagnoses / procedures / labs / readmissions\nhospitals → quarterly quality measures",language=None)
    left,right=st.columns(2)
    with left:
        st.markdown("**Designed analytical variation**")
        st.markdown("- Hospital and rural/urban differences\n- Diagnosis and comorbidity risk effects\n- Readmission, mortality, and complication variation\n- Cost and length-of-stay variation\n- Temporal trends and seasonality\n- Low-volume hospital cohorts")
    with right:
        st.markdown("**Intentional data-quality issues**")
        st.markdown("- Missing optional demographic and disposition values\n- A small number of suspicious date combinations\n- Rare categories and an inconsistent diagnosis code\n- Null-heavy optional fields\n- Small subgroups for suppression testing")
    st.warning("All data is fictional. It contains no names or real patient information and must not be used for clinical decisions, hospital ranking, or regulatory reporting.")
    st.markdown("**Good questions to explore**")
    st.markdown("Encounter volumes and trends; diagnosis prevalence; cost by diagnosis; readmission, mortality, and complication rates; length of stay; rural/urban comparisons; minimum-volume quality rankings; and approved statistical comparisons.")
with schema_tab:
    st.caption("Exact allowlisted tables and columns available to SQL validation.")
    st.json({k:sorted(v) for k,v in schema_catalog(settings.db_path).items() if k!="audit_runs"})
with registry_tab:
    st.caption("Deterministic metric definitions the model may select but may not redefine.")
    st.json({k:v.model_dump() for k,v in METRICS.items()})
