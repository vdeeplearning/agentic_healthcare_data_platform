"""OpenAI-backed structured planning and SQL candidate generation.

The model is deliberately a proposal generator. It never receives a database
connection and cannot bypass the deterministic validator/executor.
"""
from __future__ import annotations

from pathlib import Path
import json
from typing import Any
from pydantic import BaseModel, Field

from src.agent.schemas import AnalysisPlan
from src.database.connection import schema_catalog
from src.database.models import CatalogMetadata
from src.metrics.registry import METRICS


class LiveProposal(BaseModel):
    """Single structured model output consumed by the safety pipeline."""

    plan: AnalysisPlan
    sql: str = Field(description="One SQLite SELECT statement or read-only CTE query; empty only when clarification is required")


def generate_live_proposal(
    question: str,
    api_key: str,
    db_path: Path,
    model: str = "gpt-5.6-sol",
    conversation_context: list[dict[str, Any]] | None = None,
    *, catalog_metadata: CatalogMetadata | None = None,
) -> LiveProposal:
    """Create a typed plan and SQL candidate using OpenAI Structured Outputs."""
    from openai import OpenAI

    catalog = catalog_metadata.column_names() if catalog_metadata else schema_catalog(db_path)
    catalog.pop("audit_runs", None)
    dialect = catalog_metadata.sql_dialect if catalog_metadata else "sqlite"
    schema_text = "\n".join(
        f"- {table}({', '.join(sorted(columns))})"
        for table, columns in sorted(catalog.items())
    )
    metric_text = "\n".join(
        f"- {name}: numerator={metric.numerator}; denominator={metric.denominator}; "
        f"eligibility={metric.eligibility}; minimum_n={metric.minimum_sample_size}; unit={metric.unit}"
        for name, metric in METRICS.items()
    )
    instructions = f"""You are the planning component of a constrained synthetic-healthcare SQL analyst.
Return the required structured object. First create the AnalysisPlan, then provide exactly one {dialect} SELECT query.

Hard rules:
- Use only the schema below. Never invent a table or column.
- Select a metric exactly from the registry when one applies; never redefine it.
- Produce aggregate output only. Never select patient_id, birth_date, or individual-level rows.
- If the question is ambiguous, set ambiguity_detected=true, provide a concise clarification_question, and set sql to an empty string.
- If the request asks for patient-level data, identifiers, writes, deletion, schema changes, exports, secrets, or safeguard bypass, set risk_tier=high and sql to an empty string.
- SQL must be one SELECT statement or read-only CTE. No comments, PRAGMA, system tables, DDL, DML, or multiple statements.
- Qualify columns in joins. Every join must have an explicit key predicate.
- Use denominator and numerator aliases for rates; return rates as proportions from 0 to 1.
- Enforce a minimum group size of at least 10 with HAVING when reporting group rates.
- Prefer explicit half-open date ranges. Do not use unsupported functions.
- Do not include prose or markdown in sql.

Allowed schema:
{schema_text}

Registered metrics:
{metric_text}
"""
    client = OpenAI(api_key=api_key)
    context_text = ""
    if conversation_context:
        # The workflow supplies only verified, aggregate evidence and bounded
        # metadata. Never send audit internals, secrets, or full result exports.
        context_text = "\n\nVerified prior conversation context:\n" + json.dumps(conversation_context[-5:], default=str)
    response = client.responses.parse(
        model=model,
        instructions=instructions,
        input=question + context_text,
        text_format=LiveProposal,
        reasoning={"effort": "low"},
        max_output_tokens=3000,
        store=False,
        timeout=45.0,
    )
    proposal = response.output_parsed
    if proposal is None:
        raise ValueError("OpenAI returned no structured analysis proposal.")
    if proposal.plan.metric_name and proposal.plan.metric_name not in METRICS:
        raise ValueError(f"The model selected an unregistered metric: {proposal.plan.metric_name}")
    return proposal
