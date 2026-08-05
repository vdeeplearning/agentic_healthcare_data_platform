"""Transactional PostgreSQL loader for the shared logical record stream."""
from __future__ import annotations

from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from typing import Iterable
import argparse

from src.database.generator import SyntheticRecordGenerator
from src.database.lifecycle import (
    LOADER_VERSION,SCHEMA_VERSION,DatasetManifest,DatasetSnapshot,LoadResult,
    LogicalRecordBatch,manifest_identity,snapshot_identity,
)
from src.database.postgres_backend import _driver
from src.metadata.repository import ManifestStore
from src.metadata.repository import SQLiteManifestStore


ROOT=Path(__file__).resolve().parents[2]
TABLE_COLUMNS={
 "patients":("patient_id","birth_date","sex","race_ethnicity","insurance_type","residential_region","created_at"),
 "hospitals":("hospital_id","hospital_name","state","urban_rural","bed_count","teaching_status","ownership_type"),
 "providers":("provider_id","hospital_id","specialty","years_experience"),
 "encounters":("encounter_id","patient_id","hospital_id","provider_id","encounter_type","admission_date","discharge_date","discharge_disposition","total_cost","mortality_flag","complication_flag"),
 "diagnoses":("diagnosis_id","diagnosis_code","diagnosis_name","diagnosis_category"),
 "encounter_diagnoses":("encounter_id","diagnosis_id","diagnosis_rank","primary_diagnosis_flag"),
 "procedures":("procedure_id","procedure_code","procedure_name","procedure_category"),
 "encounter_procedures":("encounter_id","procedure_id","procedure_date"),
 "lab_results":("encounter_id","lab_name","lab_value","unit","reference_low","reference_high","collected_at"),
 "readmissions":("readmission_id","index_encounter_id","readmission_encounter_id","days_to_readmission","readmitted_within_30_days"),
 "quality_measures":("quality_measure_id","hospital_id","measure_name","measurement_period_start","measurement_period_end","numerator","denominator","measure_value"),
}


class PostgresLoader:
    name="postgres"; version=LOADER_VERSION

    def __init__(self,dsn:str,manifest_store:ManifestStore,schema:str="public",storage_identity:str|None=None):
        if not dsn: raise ValueError("A PostgreSQL DSN is required.")
        self._dsn=dsn; self.manifest_store=manifest_store; self.schema=schema; self.storage_identity=storage_identity or f"postgres:{schema}"

    def _ddl(self)->list[str]: return [statement.strip() for statement in (ROOT/"sql"/"postgres"/"schema.sql").read_text(encoding="utf-8").split(";") if statement.strip()]

    def load_batches(self,batches:Iterable[LogicalRecordBatch],manifest:DatasetManifest)->LoadResult:
        psycopg,sql,dict_row=_driver(); connection=psycopg.connect(self._dsn,row_factory=dict_row,autocommit=False)
        counts=Counter({entity:0 for entity in TABLE_COLUMNS})
        try:
            connection.execute("BEGIN")
            connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema)))
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
            connection.execute(sql.SQL("SET LOCAL search_path TO {}").format(sql.Identifier(self.schema)))
            for statement in self._ddl(): connection.execute(statement)
            for batch in batches:
                if batch.entity not in TABLE_COLUMNS: raise ValueError(f"Unsupported logical entity: {batch.entity}")
                records=[tuple(record)[1:] if batch.entity=="lab_results" else tuple(record) for record in batch.records]
                if records:
                    columns=TABLE_COLUMNS[batch.entity]
                    insert=sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(sql.Identifier(batch.entity),sql.SQL(",").join(map(sql.Identifier,columns)),sql.SQL(",").join(sql.Placeholder() for _ in columns))
                    with connection.cursor() as cursor: cursor.executemany(insert,records)
                    counts[batch.entity]+=len(records)
            actual={entity:connection.execute(sql.SQL("SELECT COUNT(*) AS count FROM {}").format(sql.Identifier(entity))).fetchone()["count"] for entity in TABLE_COLUMNS}
            foreign_key_errors=0
            quality_errors=connection.execute("SELECT COUNT(*) AS count FROM quality_measures WHERE numerator>denominator OR measure_value<0 OR measure_value>1").fetchone()["count"]
            mismatches={entity:{"expected":counts[entity],"actual":actual[entity]} for entity in TABLE_COLUMNS if counts[entity]!=actual[entity]}
            total_cost=float(connection.execute("SELECT ROUND(SUM(total_cost)::numeric,2) AS total FROM encounters").fetchone()["total"])
            validation={"foreign_key_errors":foreign_key_errors,"quality_measure_errors":quality_errors,"row_count_mismatches":mismatches}
            completed=not any(validation.values())
            if completed: connection.commit()
            else: connection.rollback()
        except Exception:
            connection.rollback(); raise
        finally: connection.close()
        loaded=manifest.model_copy(update={"entity_row_counts":dict(sorted(counts.items())),"load_timestamp":datetime.now(timezone.utc),"loader_backend":self.name,"stable_summaries":{"encounter_total_cost":total_cost},"load_complete":completed,"validation_summary":validation})
        return LoadResult(manifest=loaded,row_counts=actual,completed=completed,validation_summary=validation)

    def generate(self,seed:int,patients:int,encounters:int)->LoadResult:
        generator=SyntheticRecordGenerator(seed,patients,encounters); result=self.load_batches(generator.batches(),generator.manifest)
        manifest_id=manifest_identity(result.manifest); manifest=self.manifest_store.register_manifest(result.manifest.model_copy(update={"manifest_id":manifest_id}))
        previous=self.manifest_store.get_active_snapshot(self.name,self.storage_identity)
        snapshot_id=snapshot_identity(dataset_id=manifest.dataset_id,manifest_id=manifest_id,backend_name=self.name,schema_version=SCHEMA_VERSION,loader_name=self.name,loader_version=self.version,storage_identity=self.storage_identity,materialization_parameters={"fixture_profile":manifest.fixture_profile,"patients":patients,"encounters":encounters,"schema":self.schema})
        snapshot=DatasetSnapshot(snapshot_id=snapshot_id,dataset_id=manifest.dataset_id,manifest_id=manifest_id,loader_name=self.name,loader_version=self.version,backend_name=self.name,schema_version=SCHEMA_VERSION,load_timestamp=result.manifest.load_timestamp or datetime.now(timezone.utc),load_status="validated" if result.completed else "failed",storage_identity=self.storage_identity,materialization_parameters={"fixture_profile":manifest.fixture_profile,"patients":patients,"encounters":encounters,"schema":self.schema},table_row_counts=result.row_counts,validation_summary=result.validation_summary,replaces_snapshot_id=previous.snapshot_id if previous else None,provenance_metadata={"source_type":"synthetic","generator_version":manifest.generator_version})
        snapshot=self.manifest_store.register_snapshot(snapshot)
        if result.completed: snapshot=self.manifest_store.activate_snapshot(snapshot.snapshot_id)
        return result.model_copy(update={"manifest":manifest,"snapshot":snapshot})


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--dsn",required=True); parser.add_argument("--schema",default="public"); parser.add_argument("--metadata-path",type=Path,default=Path("data/generated/postgres.metadata.db")); parser.add_argument("--storage-identity",default="postgres:public"); parser.add_argument("--seed",type=int,default=42); parser.add_argument("--patients",type=int,default=25_000); parser.add_argument("--encounters",type=int,default=100_000)
    args=parser.parse_args(); result=PostgresLoader(args.dsn,SQLiteManifestStore(args.metadata_path),args.schema,args.storage_identity).generate(args.seed,args.patients,args.encounters)
    print({key:result.row_counts.get(key,0) for key in ("patients","hospitals","providers","encounters","readmissions")})


if __name__=="__main__": main()
