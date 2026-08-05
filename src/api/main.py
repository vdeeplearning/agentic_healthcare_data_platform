"""FastAPI application."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
from src.agent.schemas import AnalysisResponse
from src.agent.workflow import Analyst
from src.audit.repository import get_run,list_runs
from src.config import get_settings
from src.database.seed import generate_database
from src.database.factory import create_query_backend
from src.metadata.repository import SQLiteManifestStore,metadata_path_for
from src.demo.curated_questions import EXAMPLES
from src.metrics.registry import METRICS
from src.safety.sql_validator import validate_sql

class ConversationContext(BaseModel):
    question:str; grounded_answer:str; plan:dict[str,Any]|None=None; validated_sql:str|None=None
    verified_result_sample:list[dict[str,Any]]=Field(default_factory=list,max_length=10)
class AnalyzeRequest(BaseModel):
    question:str=Field(min_length=3,max_length=2000); api_key:str|None=None
    conversation_context:list[ConversationContext]=Field(default_factory=list,max_length=5)
class SQLRequest(BaseModel): sql:str=Field(min_length=1,max_length=20_000)

settings=get_settings(); app=FastAPI(title="Agentic Clinical SQL Analyst",version="0.1.0",description="Synthetic data only; not for clinical decisions.")
def _ensure_db()->None:
    if not settings.db_path.exists(): generate_database(settings.db_path,settings.seed,patients=2_500,encounters=10_000)
def _backend(): return create_query_backend(settings)
def _active_snapshot():
    path=settings.metadata_path or metadata_path_for(settings.db_path)
    if not path.exists(): return None
    try:
        backend=_backend(); storage=getattr(backend,"storage_identity",settings.db_path.name)
        return SQLiteManifestStore(path).get_active_snapshot(backend.name,storage)
    except Exception: return None
@app.get("/")
def root(): return {"name":app.title,"mode":"deterministic-demo" if settings.demo_mode else "configured","synthetic_data":True,"docs":"/docs"}
@app.get("/health")
def health(): return {"status":"ok","database_exists":settings.db_path.exists(),"synthetic_data":True}
@app.get("/schema")
def schema(): _ensure_db(); return {k:sorted(v) for k,v in _backend().discover_catalog().column_names().items() if k!="audit_runs"}
@app.get("/metrics")
def metrics(): return {k:v.model_dump() for k,v in METRICS.items()}
@app.post("/analyze",response_model=AnalysisResponse)
def analyze(request:AnalyzeRequest): _ensure_db(); return Analyst(settings.db_path,settings.max_rows,settings.query_timeout_seconds,settings.small_cell_threshold,query_backend=_backend(),dataset_snapshot=_active_snapshot()).analyze(request.question,request.api_key,[turn.model_dump() for turn in request.conversation_context])
@app.post("/validate-sql")
def validate(request:SQLRequest): _ensure_db(); backend=_backend(); return validate_sql(request.sql,catalog=backend.discover_catalog()).model_dump()
@app.get("/runs")
def runs(limit:int=50): _ensure_db(); return list_runs(settings.db_path,limit)
@app.get("/runs/{run_id}")
def run(run_id:str):
    _ensure_db(); result=get_run(settings.db_path,run_id)
    if result is None: raise HTTPException(404,"Run not found")
    return result
@app.get("/reference-queries")
def reference_queries(): return {"examples":EXAMPLES,"path":"sql/reference_queries"}
@app.post("/demo/reset")
def reset_demo(): return {"status":"disabled","detail":"Use `python -m src.database.seed` explicitly; reset is not exposed as a destructive HTTP action."}
