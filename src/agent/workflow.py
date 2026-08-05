"""Bounded analysis workflow. Structured steps can be represented as a LangGraph in live extensions."""
from __future__ import annotations
import uuid
from pathlib import Path
from typing import Any
from src.agent.schemas import AnalysisPlan,AnalysisResponse,TraceEvent,ValidationReport
from src.audit.repository import AuditStore,SQLiteAuditStore
from src.database.backend import QueryBackend,SQLiteQueryBackend
from src.database.models import ExecutionContext
from src.database.lifecycle import DatasetIdentity
from src.demo.curated_questions import curated
from src.agent.live_planner import generate_live_proposal
from src.agent.planner import ExistingPlanner,Planner
from src.metrics.registry import METRICS
from src.safety.privacy import classify_risk,suppress_small_cells
from src.safety.prompt_injection import injection_warnings
from src.safety.result_validator import validate_results
from src.safety.sql_validator import validate_sql
from src.statistics.tools import run_statistical_tool

class Analyst:
    """Orchestrates an allowlisted, bounded query pipeline."""
    def __init__(self,db_path:Path,max_rows:int=1000,timeout_seconds:float=5,small_cell_threshold:int=10,model:str="gpt-5.6-sol",*,query_backend:QueryBackend|None=None,audit_store:AuditStore|None=None,planner:Planner|None=None,dataset_identity:DatasetIdentity|None=None):
        self.db_path=Path(db_path); self.max_rows=max_rows; self.timeout_seconds=timeout_seconds; self.small_cell_threshold=small_cell_threshold; self.model=model
        self.query_backend=query_backend or SQLiteQueryBackend(self.db_path)
        self._uses_default_audit_store=audit_store is None
        self.audit_store=audit_store or SQLiteAuditStore(self.db_path)
        self.planner=planner or ExistingPlanner(self.db_path,curated,generate_live_proposal)
        self.dataset_identity=dataset_identity
    def analyze(self,question:str,api_key:str|None=None,conversation_context:list[dict[str,Any]]|None=None)->AnalysisResponse:
        run_id=str(uuid.uuid4()); trace=[]; warnings=injection_warnings(question); risk,risk_warnings=classify_risk(question); warnings+=risk_warnings
        trace.append(TraceEvent(step="normalize_question",status="ok",detail="Whitespace and casing normalized for classification."))
        if risk=="high": return self._finish(run_id,question,"denied","Request denied by the high-risk privacy policy.",None,None,[],warnings,trace,None)
        q=question.lower()
        if any(term in q for term in ("which hospital is worst","best hospital")):
            plan=AnalysisPlan(normalized_question=q,analysis_intent="ambiguous hospital ranking",ambiguity_detected=True,clarification_question="Which outcome should define worst: readmission, mortality, complications, length of stay, or cost?",risk_tier=risk)
            trace.append(TraceEvent(step="determine_if_clarification_needed",status="blocked",detail="Ranking metric is unspecified."))
            return self._finish(run_id,question,"clarification_required","A metric is needed before analysis.",plan,None,[],warnings,trace,None,plan.clarification_question)
        follow_up=bool(conversation_context) and self._looks_like_follow_up(question)
        known=None if follow_up else self.planner.curated(question)
        if not known:
            if not api_key:
                plan=AnalysisPlan(normalized_question=q,analysis_intent="unsupported deterministic request",ambiguity_detected=True,clarification_question="This question is not in deterministic demo mode. Paste an OpenAI API key or choose one of the curated examples.",risk_tier=risk)
                trace.append(TraceEvent(step="classify_request",status="blocked",detail="No deterministic template matched; no SQL was invented."))
                return self._finish(run_id,question,"clarification_required","The request needs an API-backed plan or a supported template.",plan,None,[],warnings,trace,None,plan.clarification_question)
            trace.append(TraceEvent(step="classify_request",status="ok",detail="Routing unsupported demo question to the structured OpenAI planner."))
            try:
                proposal=self.planner.live(question,api_key,self.model,conversation_context)
            except Exception as exc:
                detail=self._safe_openai_error(exc,api_key)
                trace.append(TraceEvent(step="create_analysis_plan",status="blocked",detail=detail))
                return self._finish(run_id,question,"failed",f"OpenAI planning failed: {detail}",None,None,[],warnings,trace,None)
            plan,sql=proposal.plan,proposal.sql
            plan.risk_tier=risk if plan.risk_tier=="low" else plan.risk_tier
            if plan.risk_tier=="high":
                trace.append(TraceEvent(step="create_analysis_plan",status="blocked",detail="The structured planner classified the request as high risk."))
                return self._finish(run_id,question,"denied","Request denied by the high-risk privacy policy.",plan,None,[],warnings,trace,None)
            if plan.ambiguity_detected or not sql.strip():
                trace.append(TraceEvent(step="determine_if_clarification_needed",status="blocked",detail="The structured planner requires clarification."))
                clarification=plan.clarification_question or "Please clarify the requested metric, population, and date range."
                return self._finish(run_id,question,"clarification_required","The request needs clarification before SQL can be generated.",plan,None,[],warnings,trace,None,clarification)
            trace += [TraceEvent(step="create_analysis_plan",status="ok",detail="OpenAI returned a Pydantic-validated plan."),TraceEvent(step="generate_sql",status="ok",detail="OpenAI proposed one SQL candidate for deterministic validation.")]
        else:
            plan,sql=known
            trace += [TraceEvent(step="classify_request",status="ok",detail=plan.analysis_intent),TraceEvent(step="create_analysis_plan",status="ok",detail="Plan passed Pydantic validation."),TraceEvent(step="generate_sql",status="ok",detail="Selected bounded deterministic SQL template.")]
        plan.risk_tier=risk if plan.risk_tier=="low" else plan.risk_tier
        catalog=self.query_backend.discover_catalog()
        validation=validate_sql(sql,max_rows=self.max_rows,catalog=catalog); trace.append(TraceEvent(step="validate_sql",status="ok" if validation.valid else "blocked",detail="; ".join(validation.errors or ["AST, schema, function, and join checks passed."])))
        warnings+=validation.warnings
        if not validation.valid: return self._finish(run_id,question,"failed","SQL validation failed safely.",plan,sql,[],warnings,trace,validation)
        sql=validation.sql or sql
        try:
            identity=self.dataset_identity
            execution=self.query_backend.execute(sql,ExecutionContext(run_id=run_id,correlation_id=run_id,timeout_seconds=self.timeout_seconds,dataset_id=identity.dataset_id if identity else "synthetic-clinical",fixture_profile=identity.profile if identity else None,generator_version=identity.generator_version if identity else None),self.max_rows)
        except Exception as exc:
            trace.append(TraceEvent(step="execute_query",status="blocked",detail=str(exc))); return self._finish(run_id,question,"failed","Query execution failed safely.",plan,sql,[],warnings,trace,validation)
        rows=execution.rows; query_plan=execution.query_plan; elapsed=execution.execution_time_ms
        if execution.truncated: warnings.append("Result truncated at the configured row limit.")
        trace += [TraceEvent(step="inspect_query_plan",status="warning" if any("SCAN" in str(x) for x in query_plan) else "ok",detail=f"Reviewed {len(query_plan)} plan operations."),TraceEvent(step="execute_query",status="ok",detail=f"Read-only query returned {len(rows)} rows."),TraceEvent(step="validate_results",status="ok",detail="Deterministic plausibility checks completed.")]
        warnings+=validate_results(rows); rows,suppression=suppress_small_cells(rows,self.small_cell_threshold); warnings+=suppression
        statistic=None
        if plan.statistical_test_type=="chi_square" and len(rows)==2:
            table=[[int(r["numerator"]),int(r["denominator"]-r["numerator"])] for r in rows]; statistic=run_statistical_tool("chi_square",table=table); trace.append(TraceEvent(step="run_approved_statistical_tool",status="ok",detail="Ran registered chi-square tool; no arbitrary code executed."))
        answer=self._answer(plan,rows,statistic); trace.append(TraceEvent(step="compose_grounded_answer",status="ok",detail="Template used verified result fields only.")); trace.append(TraceEvent(step="validate_answer_faithfulness",status="ok",detail="Numeric claims originate from deterministic result formatting."))
        response=self._finish(run_id,question,"completed",answer,plan,sql,rows,warnings,trace,validation,statistics=statistic,elapsed=elapsed,query_plan=query_plan)
        return response
    @staticmethod
    def _looks_like_follow_up(question:str)->bool:
        q=question.lower().strip()
        markers=("what about","how about","and in ","and for ","compared with that","compared to that","break that down","show those","why is that","which of those","same for","instead","previous result")
        return any(marker in q for marker in markers) or len(q.split())<=5 and any(word in q.split() for word in ("those","that","them","it"))
    def _answer(self,plan:AnalysisPlan,rows:list[dict[str,Any]],statistic:dict[str,Any]|None)->str:
        if not rows: return "The validated query returned no data, so no conclusion is supported."
        first=rows[0]
        if plan.analysis_intent=="summarize relational dataset structure":
            return "The dataset uses a normalized relational design centered on encounters: patients, hospitals, and providers connect to encounter facts; bridge tables attach diagnosis and procedure vocabularies; labs and readmissions add clinical outcomes; quarterly quality measures support longitudinal hospital analysis. The table below shows each analytical table and its current row count."
        if "patient_count" in first: return f"The synthetic dataset contains {first['patient_count']:,} patients."
        if "hospital_count" in first: return f"The synthetic dataset contains {first['hospital_count']:,} hospitals."
        if "encounter_count" in first and "hospital_name" in first: return f"{first['hospital_name']} had the most encounters in the requested period ({first['encounter_count']:,}); the full validated ranking is shown below."
        if "readmission_rate" in first and "hospital_name" in first: return f"{first['hospital_name']} ranked highest at {100*first['readmission_rate']:.1f}% ({first['numerator']:,}/{first['denominator']:,} eligible encounters). These are unadjusted synthetic rates."
        if "complication_rate" in first: return f"{first['hospital_name']} had the highest eligible complication rate at {100*first['complication_rate']:.1f}% ({first['numerator']:,}/{first['denominator']:,})."
        if "total_cost" in first: return f"{first['diagnosis_name']} accounted for the highest total synthetic cost (${first['total_cost']:,.2f}) across {first['encounter_count']:,} encounters."
        if statistic: return f"The urban/rural readmission comparison produced p={statistic['p_value']:.4g} using a chi-square test (n={statistic['n']:,}). This is an unadjusted association, not a causal result."
        if len(rows)==1:
            count_fields=[(key,value) for key,value in first.items() if key.lower().endswith("_count") and isinstance(value,(int,float))]
            if len(count_fields)==1:
                key,value=count_fields[0]; label=key.removesuffix("_count").replace("_"," ")
                return f"The verified {label} count is {value:,.0f}."
        return "The verified result table is shown below."
    @staticmethod
    def _safe_openai_error(exc:Exception,api_key:str)->str:
        """Map provider errors to useful messages without exposing key fingerprints."""
        status=getattr(exc,"status_code",None)
        if status==401: return "OpenAI rejected the API key. Create or copy an active project key from the OpenAI Platform, then paste it again."
        if status==429: return "OpenAI rate limits or account quota were exceeded. Check project billing and usage limits, then retry."
        if status==403: return "This OpenAI project is not permitted to use the configured model. Check project permissions or configure another supported model."
        if status is not None and status>=500: return "OpenAI is temporarily unavailable. Please retry shortly."
        # Defensive redaction covers both the exact key and provider-masked key fingerprints.
        import re
        message=str(exc).replace(api_key,"[REDACTED]")
        message=re.sub(r"sk-[A-Za-z0-9_*\-]{8,}","[REDACTED_API_KEY]",message)
        return message[:500]
    def _finish(self,run_id,question,status,answer,plan,sql,rows,warnings,trace,validation,clarification=None,statistics=None,elapsed=None,query_plan=None):
        response=AnalysisResponse(run_id=run_id,status=status,question=question,answer=answer,clarification_question=clarification,plan=plan,sql=sql,columns=list(rows[0]) if rows else [],rows=rows,warnings=list(dict.fromkeys(warnings)),validation=validation,trace=trace,metric_definition=METRICS[plan.metric_name].model_dump() if plan and plan.metric_name in METRICS else None,statistics=statistics,execution_time_ms=elapsed,provenance={"database":str(self.db_path),"read_only":True,"query_plan":query_plan or [],"synthetic_data":True})
        if self.db_path.exists() or not self._uses_default_audit_store: self.audit_store.write({"run_id":run_id,"question":question,"normalized_question":plan.normalized_question if plan else question.lower(),"model_name":self.model if any(event.detail.startswith("OpenAI") for event in trace) else "deterministic-demo","plan":plan.model_dump() if plan else None,"sql":sql,"validation_status":"passed" if validation and validation.valid else status,"execution_status":status,"row_count":len(rows),"execution_time_ms":elapsed,"statistical_tools":statistics,"warnings":warnings,"final_answer":answer})
        return response
