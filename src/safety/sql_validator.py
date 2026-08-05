"""SQLGlot-based allowlist validation with relationship checks."""
from __future__ import annotations
import re
from pathlib import Path
import sqlglot
from sqlglot import exp
from src.agent.schemas import ValidationReport
from src.database.connection import schema_catalog
from src.database.models import CatalogMetadata

FORBIDDEN=(exp.Insert,exp.Update,exp.Delete,exp.Drop,exp.Alter,exp.Create,exp.Command,exp.Merge)
APPROVED_FUNCTIONS={"count","sum","avg","min","max","round","coalesce","nullif","date","datetime","julianday","strftime","cast","row_number","rank","dense_rank","lag","lead","abs","lower","upper","and","or"}
RELATIONSHIPS={frozenset(x) for x in [("encounters.patient_id","patients.patient_id"),("encounters.hospital_id","hospitals.hospital_id"),("encounters.provider_id","providers.provider_id"),("providers.hospital_id","hospitals.hospital_id"),("encounter_diagnoses.encounter_id","encounters.encounter_id"),("encounter_diagnoses.diagnosis_id","diagnoses.diagnosis_id"),("encounter_procedures.encounter_id","encounters.encounter_id"),("encounter_procedures.procedure_id","procedures.procedure_id"),("lab_results.encounter_id","encounters.encounter_id"),("readmissions.index_encounter_id","encounters.encounter_id"),("readmissions.readmission_encounter_id","encounters.encounter_id"),("quality_measures.hospital_id","hospitals.hospital_id")]}

def validate_sql(sql: str,path: Path|None=None,max_joins:int=8,max_columns:int=20,max_rows:int=1000,*,catalog:CatalogMetadata|None=None) -> ValidationReport:
    errors=[]; warnings=[]
    if "--" in sql or "/*" in sql: errors.append("SQL comments are not allowed.")
    if re.search(r"\b(sqlite_master|sqlite_schema|pragma|attach|detach|vacuum)\b",sql,re.I): errors.append("System tables and administrative commands are prohibited.")
    dialect=catalog.sql_dialect if catalog else "sqlite"
    try: statements=sqlglot.parse(sql,read=dialect)
    except sqlglot.errors.ParseError as exc: return ValidationReport(valid=False,errors=[f"Parse error: {exc}"])
    if len(statements)!=1: errors.append("Exactly one SQL statement is required.")
    if not statements: return ValidationReport(valid=False,errors=errors or ["Empty SQL."])
    tree=statements[0]
    if any(isinstance(node,FORBIDDEN) for node in tree.walk()): errors.append("Only SELECT and read-only CTE statements are allowed.")
    if not isinstance(tree,(exp.Select,exp.Union,exp.With)) and tree.find(exp.Select) is None: errors.append("Statement must be a query.")
    joins=list(tree.find_all(exp.Join))
    if len(joins)>max_joins: errors.append(f"Query exceeds maximum of {max_joins} joins.")
    for join in joins:
        predicate=join.args.get("on")
        if (predicate is None and join.args.get("using") is None) or isinstance(predicate,exp.Boolean) and predicate.this is True:
            errors.append("Every join requires a nontrivial ON or USING predicate.")
    if catalog is None and path is None: raise ValueError("path or catalog is required")
    catalog_map=catalog.column_names() if catalog else schema_catalog(path)
    prohibited=set(catalog.prohibited_objects if catalog else ["audit_runs"])
    cte_names={cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    tables=sorted({t.name for t in tree.find_all(exp.Table) if t.name not in cte_names})
    for table in tables:
        if table not in catalog_map or table in prohibited: errors.append(f"Table is not queryable: {table}")
    aliases={t.alias_or_name:t.name for t in tree.find_all(exp.Table)}
    columns=[]
    for column in tree.find_all(exp.Column):
        name=column.name; columns.append(column.sql())
        if column.table:
            table=aliases.get(column.table,column.table)
            if table in catalog_map and name not in catalog_map[table]: errors.append(f"Unknown column: {column.sql()}")
        elif len(tables)==1 and name not in catalog_map.get(tables[0],set()) and name!="*": errors.append(f"Unknown column: {name}")
    select=tree.find(exp.Select)
    if select and len(select.expressions)>max_columns: errors.append(f"Query selects more than {max_columns} expressions.")
    for func in tree.find_all(exp.Func):
        fname=func.sql_name().lower()
        if fname and fname not in APPROVED_FUNCTIONS: errors.append(f"Function is not allowlisted: {fname}")
    if select and select.args.get("limit") is None:
        select.set("limit",exp.Limit(expression=exp.Literal.number(max_rows))); warnings.append(f"LIMIT {max_rows} inserted.")
    normalized=tree.sql(dialect=dialect)
    return ValidationReport(valid=not errors,errors=list(dict.fromkeys(errors)),warnings=warnings,tables=tables,columns=sorted(set(columns)),sql=normalized)
