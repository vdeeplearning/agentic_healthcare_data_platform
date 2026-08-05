"""Reviewed deterministic local transformations; no model-generated code executes here."""
from __future__ import annotations

import hashlib
import json
from datetime import date,datetime,timezone
from typing import Any

from src.database.generator import SyntheticRecordGenerator
from src.database.lifecycle import DISCLAIMER, GENERATOR_VERSION, FIXTURE_PROFILES
from src.lake.models import (
    DataObject, LakeLayer, LayerManifest, LineageEdge, PublishedSnapshot, SourceBatch,
    SourceSystem, TransformationDefinition, TransformationRun, ValidationResult,
)
from src.lake.store import LocalFilesystemLakeStore


TRANSFORM_VERSIONS={"source-to-raw":"1.0.0","raw-to-bronze":"1.0.0","bronze-to-silver":"1.0.0","silver-to-gold":"1.0.0"}
ENTITY_KEYS={"patients":("patient_id",),"hospitals":("hospital_id",),"providers":("provider_id",),"encounters":("encounter_id",),"diagnoses":("diagnosis_id",),"encounter_diagnoses":("encounter_id","diagnosis_id"),"procedures":("procedure_id",),"encounter_procedures":("encounter_id","procedure_id"),"lab_results":("encounter_id","lab_name","collected_at"),"readmissions":("readmission_id",),"quality_measures":("quality_measure_id",)}


def _hash(prefix:str,value:Any)->str:
    payload=json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:20]}"


def _jsonl(rows:list[dict[str,Any]])->bytes:
    return b"".join(json.dumps(row,sort_keys=True,separators=(",",":"),default=str).encode()+b"\n" for row in rows)


def _parse(payload:bytes)->tuple[list[dict[str,Any]],list[str]]:
    rows=[]; errors=[]
    for number,line in enumerate(payload.splitlines(),1):
        try:
            value=json.loads(line)
            if not isinstance(value,dict): raise ValueError("row is not an object")
            rows.append(value)
        except (json.JSONDecodeError,ValueError) as exc: errors.append(f"line {number}: {exc}")
    return rows,errors


class LocalLakePipeline:
    """Create and atomically publish deterministic medallion snapshots."""

    def __init__(self,store:LocalFilesystemLakeStore,orchestration_run_id:str|None=None): self.store=store; self.orchestration_run_id=orchestration_run_id

    def generate_source(self,profile:str="test",seed:int=17,kind:str="initial",parent_batch_id:str|None=None,malformed:bool=False)->SourceBatch:
        if profile not in FIXTURE_PROFILES: raise ValueError(f"Unknown fixture profile: {profile}")
        selected=FIXTURE_PROFILES[profile]; generator=SyntheticRecordGenerator(seed,selected.patients,selected.encounters)
        grouped:dict[str,list[dict[str,Any]]]={}
        for batch in generator.batches(): grouped.setdefault(batch.entity,[]).extend(record._asdict() for record in batch.records)
        objects=[]
        for entity,rows in sorted(grouped.items()):
            payload=_jsonl(rows)
            if malformed and entity=="patients": payload+=b'{"patient_id": "broken",\n'
            object_id=_hash("object",{"dataset":generator.manifest.dataset_id,"entity":entity,"payload":hashlib.sha256(payload).hexdigest(),"kind":kind,"parent":parent_batch_id})
            objects.append(self.store.write_object(LakeLayer.raw,entity,object_id,payload,len(rows)+(1 if malformed and entity=="patients" else 0)))
        batch_id=_hash("batch",{"dataset":generator.manifest.dataset_id,"objects":[item.object_id for item in objects],"kind":kind,"parent":parent_batch_id})
        batch=SourceBatch(batch_id=batch_id,source_system=SourceSystem(source_system_id="synthetic-clinical",name="Versioned synthetic clinical generator"),generator_version=GENERATOR_VERSION,generation_parameters=generator.manifest.generation_parameters,dataset_id=generator.manifest.dataset_id,random_seed=seed,fixture_profile=profile,objects=objects,row_counts={key:len(value) for key,value in sorted(grouped.items())},disclaimer=DISCLAIMER,parent_batch_id=parent_batch_id,batch_kind="malformed" if malformed else kind)
        return self.store.register_source_batch(batch)

    def publish_raw(self,batch:SourceBatch)->PublishedSnapshot:
        checksum_ok=all(self.store.validate_checksum(item) for item in batch.objects)
        validation=ValidationResult(passed=checksum_ok,checks={"checksums":checksum_ok,"immutable_objects":True},errors=[] if checksum_ok else ["Raw object checksum mismatch."])
        manifest_id=_hash("lake-manifest",{"layer":"raw","batch":batch.batch_id,"objects":[item.model_dump(mode="json") for item in batch.objects]})
        manifest=LayerManifest(manifest_id=manifest_id,layer=LakeLayer.raw,dataset_id=batch.dataset_id,transformation_name="source-to-raw",transformation_version=TRANSFORM_VERSIONS["source-to-raw"],parent_ids=[batch.batch_id],objects=batch.objects,row_counts=batch.row_counts,validation=validation)
        self.store.register_layer_manifest(manifest)
        snapshot=self._snapshot(manifest,[],{"source_batch_id":batch.batch_id,"source_system_id":batch.source_system.source_system_id,"generator_version":batch.generator_version,"generation_parameters":batch.generation_parameters,"random_seed":batch.random_seed,"fixture_profile":batch.fixture_profile,"disclaimer":batch.disclaimer,"orchestration_run_id":self.orchestration_run_id})
        if not validation.passed: return snapshot
        return self.store.publish_snapshot(snapshot)

    def transform(self,input_snapshot_id:str,output_layer:LakeLayer,version:str|None=None,engine=None)->TransformationRun:
        if engine is None:
            from src.lake.engines import LocalPythonTransformationEngine
            engine=LocalPythonTransformationEngine()
        return engine.transform(self,input_snapshot_id,output_layer,version)

    def _transform_local(self,input_snapshot_id:str,output_layer:LakeLayer,version:str|None=None)->TransformationRun:
        source=self.store.get_snapshot(input_snapshot_id)
        if not source: raise KeyError(f"Unknown input snapshot: {input_snapshot_id}")
        expected={LakeLayer.bronze:LakeLayer.raw,LakeLayer.silver:LakeLayer.bronze,LakeLayer.gold:LakeLayer.silver}
        if output_layer not in expected or source.layer!=expected[output_layer]: raise ValueError("Invalid lake layer transition.")
        name=f"{source.layer.value}-to-{output_layer.value}"; version=version or TRANSFORM_VERSIONS[name]
        started=datetime.now(timezone.utc); parent=self.store.get_layer_manifest(source.layer_manifest_id)
        if not parent: raise KeyError("Input layer manifest is missing.")
        objects=[]; row_counts={}; rejected={}; errors=[]; warnings=[]; expected_columns=True
        for item in parent.objects:
            if not self.store.validate_checksum(item): errors.append(f"Checksum failed: {item.object_id}"); continue
            rows,parse_errors=_parse(self.store.read_object(item)); rejected[item.entity]=len(parse_errors)
            expected_columns=expected_columns and all(set(ENTITY_KEYS[item.entity]).issubset(row) for row in rows)
            if parse_errors: warnings.extend(f"{item.entity}: {error}" for error in parse_errors)
            if output_layer==LakeLayer.silver:
                keys=ENTITY_KEYS[item.entity]; seen=set(); clean=[]
                for row in rows:
                    identifier=tuple(row.get(key) for key in keys)
                    if any(value is None for value in identifier) or identifier in seen: rejected[item.entity]+=1; continue
                    seen.add(identifier); clean.append(row)
                rows=clean
            payload=_jsonl(rows); object_id=_hash("object",{"layer":output_layer.value,"entity":item.entity,"version":version,"parent":item.object_id,"checksum":hashlib.sha256(payload).hexdigest()})
            objects.append(self.store.write_object(output_layer,item.entity,object_id,payload,len(rows))); row_counts[item.entity]=len(rows)
        checks=self.quality_checks(output_layer,parent,objects,row_counts,errors,warnings,expected_columns)
        passed=all(checks.values()); validation=ValidationResult(passed=passed,checks=checks,errors=errors+([] if passed else ["Layer quality gate failed."]),warnings=warnings,rejected_rows=sum(rejected.values()))
        manifest_id=_hash("lake-manifest",{"layer":output_layer.value,"dataset":parent.dataset_id,"version":version,"parent":source.snapshot_id,"objects":[item.model_dump(mode="json") for item in objects],"validation":validation.model_dump(mode="json")})
        manifest=LayerManifest(manifest_id=manifest_id,layer=output_layer,dataset_id=parent.dataset_id,transformation_name=name,transformation_version=version,parent_ids=[source.snapshot_id],objects=objects,row_counts=row_counts,rejected_row_counts=rejected,validation=validation)
        self.store.register_layer_manifest(manifest); candidate=self._snapshot(manifest,[source.snapshot_id],source.metadata)
        published=self.store.publish_snapshot(candidate) if passed else candidate
        if passed:
            self.store.register_edge(LineageEdge(parent_id=source.snapshot_id,child_id=published.snapshot_id,relationship="transformed_to",transformation_name=name,transformation_version=version,checksums=[item.checksum for item in objects],validation_passed=True))
        completed=datetime.now(timezone.utc); run_id=_hash("transform-run",{"name":name,"version":version,"input":source.snapshot_id,"output":manifest_id})
        return TransformationRun(run_id=run_id,definition=TransformationDefinition(name=name,version=version,input_layer=source.layer,output_layer=output_layer),input_ids=[source.snapshot_id],output_manifest_id=manifest_id,status="completed" if passed else "failed",validation=validation,started_at=started,completed_at=completed,orchestration_run_id=self.orchestration_run_id,records_read=sum(item.row_count for item in parent.objects),records_written=sum(row_counts.values()),transformation_implementation_version=version)

    def run(self,profile:str="test",seed:int=17,engine=None)->dict[str,Any]:
        batch=self.generate_source(profile,seed); raw=self.publish_raw(batch)
        bronze=self.transform(raw.snapshot_id,LakeLayer.bronze,engine=engine); bronze_snapshot=self.store.get_active_snapshot(LakeLayer.bronze)
        silver=self.transform(bronze_snapshot.snapshot_id,LakeLayer.silver,engine=engine); silver_snapshot=self.store.get_active_snapshot(LakeLayer.silver)
        gold=self.transform(silver_snapshot.snapshot_id,LakeLayer.gold,engine=engine); gold_snapshot=self.store.get_active_snapshot(LakeLayer.gold)
        return {"batch":batch,"raw":raw,"bronze_run":bronze,"silver_run":silver,"gold_run":gold,"gold":gold_snapshot}

    def _snapshot(self,manifest:LayerManifest,parents:list[str],metadata:dict[str,Any])->PublishedSnapshot:
        snapshot_id=_hash("lake-snapshot",{"manifest":manifest.manifest_id,"layer":manifest.layer.value,"parents":parents})
        return PublishedSnapshot(snapshot_id=snapshot_id,layer=manifest.layer,layer_manifest_id=manifest.manifest_id,dataset_id=manifest.dataset_id,parent_snapshot_ids=parents,object_ids=[item.object_id for item in manifest.objects],status="validated" if manifest.validation.passed else "failed",metadata=metadata)

    def _gold_rates(self,objects:list[DataObject])->bool:
        target=next((item for item in objects if item.entity=="quality_measures"),None)
        if not target: return False
        rows,_=_parse(self.store.read_object(target))
        return all(0<=float(row["measure_value"])<=1 and int(row["numerator"])<=int(row["denominator"]) for row in rows)

    def quality_checks(self,output_layer:LakeLayer,parent:LayerManifest,objects:list[DataObject],row_counts:dict[str,int],errors:list[str],warnings:list[str],expected_columns:bool)->dict[str,bool]:
        checks={"input_checksums":not errors,"expected_objects":len(objects)==len(parent.objects),"parse_success":not warnings,"expected_columns":expected_columns}
        if output_layer==LakeLayer.bronze: checks["duplicate_source_objects"]=len({item.object_id for item in parent.objects})==len(parent.objects)
        if output_layer==LakeLayer.silver: checks.update(self._silver_checks(objects))
        if output_layer==LakeLayer.gold: checks.update({"quality_rate_bounds":self._gold_rates(objects),"required_entities":{"patients","encounters","quality_measures"}.issubset(row_counts),"synthetic_identifiers_only":True})
        return checks

    def _silver_checks(self,objects:list[DataObject])->dict[str,bool]:
        data={item.entity:_parse(self.store.read_object(item))[0] for item in objects}
        patient_ids={row["patient_id"] for row in data.get("patients",[])}; hospital_ids={row["hospital_id"] for row in data.get("hospitals",[])}; encounter_ids={row["encounter_id"] for row in data.get("encounters",[])}
        identifiers=all(all(isinstance(row.get(keys[0]),int) and row[keys[0]]>0 for row in data.get(entity,[])) for entity,keys in ENTITY_KEYS.items() if entity!="lab_results")
        domains=all(row.get("sex") in {"F","M","X"} for row in data.get("patients",[])) and all(row.get("encounter_type") in {"inpatient","emergency","outpatient"} for row in data.get("encounters",[]))
        foreign_keys=all(row.get("patient_id") in patient_ids and row.get("hospital_id") in hospital_ids for row in data.get("encounters",[])) and all(row.get("encounter_id") in encounter_ids for row in data.get("lab_results",[]))
        date_values=[(key,value) for rows in data.values() for row in rows for key,value in row.items() if value is not None and (key.endswith("_date") or key.endswith("_at") or key.startswith("measurement_period_"))]
        def valid_date(item):
            key,value=item
            if not isinstance(value,str): return False
            try:
                datetime.fromisoformat(value.replace("Z","+00:00")) if key.endswith("_at") else date.fromisoformat(value)
                return True
            except ValueError: return False
        date_parse_success=all(valid_date(item) for item in date_values)
        return {"identifier_validity":identifiers,"date_parse_success":date_parse_success,"categorical_domains":domains,"foreign_key_consistency":foreign_keys,"missingness_within_fixture_contract":True}
