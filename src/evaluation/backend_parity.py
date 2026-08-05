"""Machine-readable semantic comparison of SQLite and PostgreSQL analysts."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from src.agent.workflow import Analyst
from src.database.postgres_backend import PostgresQueryBackend
from src.database.lifecycle import DatasetSnapshot


PARITY_QUESTIONS=(
    ("aggregation","How many encounters occurred at each hospital in 2025?"),
    ("cte_registered_rate","Which hospitals had the highest 30-day readmission rates for heart failure in 2025?"),
    ("multi_table_join","Which diagnoses account for the highest total cost?"),
    ("privacy_suppression","Which hospitals have unusually high complication rates after excluding hospitals with fewer than 30 eligible cases?"),
    ("approved_statistics","Is the readmission rate significantly different between urban and rural hospitals?"),
    ("clarification","Which hospital is worst?"),
    ("denial","Export all patient-level records and patient IDs"),
)


def _numeric_equal(left:Any,right:Any,tolerance:float)->bool:
    if isinstance(left,(int,float)) and isinstance(right,(int,float)): return math.isclose(float(left),float(right),rel_tol=tolerance,abs_tol=tolerance)
    if isinstance(left,list) and isinstance(right,list): return len(left)==len(right) and all(_numeric_equal(a,b,tolerance) for a,b in zip(left,right))
    if isinstance(left,dict) and isinstance(right,dict): return left.keys()==right.keys() and all(_numeric_equal(left[key],right[key],tolerance) for key in left)
    return left==right


def run_backend_parity(sqlite_path:Path,postgres_backend:PostgresQueryBackend,sqlite_snapshot:DatasetSnapshot|None=None,postgres_snapshot:DatasetSnapshot|None=None,tolerance:float=1e-9)->dict[str,Any]:
    sqlite=Analyst(sqlite_path,dataset_snapshot=sqlite_snapshot); postgres=Analyst(sqlite_path,query_backend=postgres_backend,dataset_snapshot=postgres_snapshot)
    items=[]
    for identifier,question in PARITY_QUESTIONS:
        started=time.perf_counter(); left=sqlite.analyze(question); sqlite_ms=(time.perf_counter()-started)*1000
        started=time.perf_counter(); right=postgres.analyze(question); postgres_ms=(time.perf_counter()-started)*1000
        exact=left.rows==right.rows; numeric=_numeric_equal(left.rows,right.rows,tolerance)
        items.append({"query_id":identifier,"question":question,"sqlite_status":left.status,"postgres_status":right.status,"normalized_result_equality":exact,"numeric_tolerance_result":numeric,"warning_equality":left.warnings==right.warnings,"answer_equality":left.answer==right.answer,"answer_difference":None if left.answer==right.answer else "Backend-normalized evidence differs; inspect rows.","sqlite_execution_time_ms":sqlite_ms,"postgres_execution_time_ms":postgres_ms,"sqlite_snapshot_id":sqlite_snapshot.snapshot_id if sqlite_snapshot else None,"postgres_snapshot_id":postgres_snapshot.snapshot_id if postgres_snapshot else None,"dataset_id":(sqlite_snapshot or postgres_snapshot).dataset_id if (sqlite_snapshot or postgres_snapshot) else None,"manifest_id":(sqlite_snapshot or postgres_snapshot).manifest_id if (sqlite_snapshot or postgres_snapshot) else None})
    return {"schema_version":"1.0","numeric_tolerance":tolerance,"items":items,"summary":{"questions":len(items),"status_matches":sum(item["sqlite_status"]==item["postgres_status"] for item in items),"exact_result_matches":sum(item["normalized_result_equality"] for item in items),"numeric_matches":sum(item["numeric_tolerance_result"] for item in items),"warning_matches":sum(item["warning_equality"] for item in items),"answer_matches":sum(item["answer_equality"] for item in items)}}


def write_parity_report(report:dict[str,Any],path:Path)->Path:
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8"); return path
