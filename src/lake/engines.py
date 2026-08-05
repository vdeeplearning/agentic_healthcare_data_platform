"""Optional transformation engines; Spark executes reviewed policy, never model code."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime,timezone
from typing import Protocol

from src.lake.models import DataObject,LakeLayer,LayerManifest,LineageEdge,PublishedSnapshot,TransformationDefinition,TransformationRun,ValidationResult
from src.lake.pipeline import ENTITY_KEYS,TRANSFORM_VERSIONS,_hash,_jsonl,_parse
from src.lake.spark_schemas import ENTITY_FIELDS,physical_schema_for
from src.lake.spark_session import SparkSessionFactory,SparkSessionSettings


class LakeTransformationEngine(Protocol):
    name: str
    def transform(self,pipeline,input_snapshot_id:str,output_layer:LakeLayer,version:str|None=None)->TransformationRun: ...
    def close(self)->None: ...


class LocalPythonTransformationEngine:
    name="python"
    def transform(self,pipeline,input_snapshot_id:str,output_layer:LakeLayer,version:str|None=None)->TransformationRun:
        return pipeline._transform_local(input_snapshot_id,output_layer,version)
    def close(self)->None: pass


def create_transformation_engine(settings,store=None)->LakeTransformationEngine:
    if settings.lake_transform_engine=="python": return LocalPythonTransformationEngine()
    session=SparkSessionSettings(master=settings.spark_master,shuffle_partitions=settings.spark_shuffle_partitions,log_level=settings.spark_log_level,warehouse_dir=(store.root/"staging"/"spark-warehouse") if store else None)
    return PySparkTransformationEngine(session)


class PySparkTransformationEngine:
    """PySpark implementation that emits Parquet plus canonical logical sidecars."""
    name="spark"

    def __init__(self,settings:SparkSessionSettings|None=None,session_factory:SparkSessionFactory|None=None,output_partitions:int=2):
        self.settings=settings or SparkSessionSettings(); self.factory=session_factory or SparkSessionFactory(self.settings); self.output_partitions=max(1,output_partitions)
    def close(self)->None: self.factory.stop()

    @staticmethod
    def _physical_rows(rows,source_batch_id):
        values=[]
        for index,row in enumerate(rows):
            canonical=json.dumps(row,sort_keys=True,separators=(",",":"),default=str)
            values.append({**row,"_lake_row_order":index,"_lake_source_batch_id":source_batch_id,"_lake_record_hash":hashlib.sha256(canonical.encode()).hexdigest(),"_lake_quality_flags":[],"_lake_rejection_reason":None})
        return values

    @staticmethod
    def _logical_rows(frame,entity):
        fields=[name for name,_,_ in ENTITY_FIELDS[entity]]
        rows=[{name:value for name,value in row.asDict(recursive=True).items() if name in fields} for row in frame.select(*fields).collect()]
        return sorted(rows,key=lambda row:json.dumps(row,sort_keys=True,separators=(",",":"),default=str))

    def transform(self,pipeline,input_snapshot_id:str,output_layer:LakeLayer,version:str|None=None)->TransformationRun:
        source=pipeline.store.get_snapshot(input_snapshot_id)
        if not source: raise KeyError(f"Unknown input snapshot: {input_snapshot_id}")
        expected={LakeLayer.bronze:LakeLayer.raw,LakeLayer.silver:LakeLayer.bronze,LakeLayer.gold:LakeLayer.silver}
        if output_layer not in expected or source.layer!=expected[output_layer]: raise ValueError("Invalid lake layer transition.")
        parent=pipeline.store.get_layer_manifest(source.layer_manifest_id)
        if not parent: raise KeyError("Input layer manifest is missing.")
        name=f"{source.layer.value}-to-{output_layer.value}"; version=version or TRANSFORM_VERSIONS[name]; started=datetime.now(timezone.utc); spark=self.factory.create()
        objects=[]; row_counts={}; rejected={}; errors=[]; warnings=[]; expected_columns=True; input_partitions=0; output_partitions=0
        source_batch_id=source.metadata.get("source_batch_id")
        for item in parent.objects:
            if not pipeline.store.validate_checksum(item): errors.append(f"Checksum failed: {item.object_id}"); continue
            rows,parse_errors=_parse(pipeline.store.read_object(item)); rejected[item.entity]=len(parse_errors); warnings.extend(f"{item.entity}: {error}" for error in parse_errors)
            expected_columns=expected_columns and all(set(ENTITY_KEYS[item.entity]).issubset(row) for row in rows)
            if item.format=="parquet":
                path=pipeline.store.physical_object_path(item); frame=spark.read.schema(physical_schema_for(item.entity,source.layer)).parquet(str(path))
            else:
                physical=self._physical_rows(rows,source_batch_id); frame=spark.createDataFrame(physical,physical_schema_for(item.entity,source.layer))
            input_partitions+=frame.rdd.getNumPartitions()
            if output_layer==LakeLayer.silver:
                from functools import reduce
                from pyspark.sql import functions as functions
                keys=list(ENTITY_KEYS[item.entity]); predicate=reduce(lambda left,right:left&right,[functions.col(key).isNotNull() for key in keys])
                before=frame.count(); frame=frame.filter(predicate).dropDuplicates(keys); rejected[item.entity]+=before-frame.count()
            logical=self._logical_rows(frame,item.entity); payload=_jsonl(logical)
            object_id=_hash("object",{"layer":output_layer.value,"entity":item.entity,"version":version,"engine":"spark","format":"parquet","parent":item.object_id,"logical_checksum":hashlib.sha256(payload).hexdigest()})
            output_frame=spark.createDataFrame(self._physical_rows(logical,source_batch_id),physical_schema_for(item.entity,output_layer)).repartition(self.output_partitions)
            staging=pipeline.store.spark_staging_path(f"spark-{object_id}")
            try:
                output_frame.write.mode("overwrite").parquet(str(staging)); output_partitions+=output_frame.rdd.getNumPartitions()
                objects.append(pipeline.store.publish_parquet_object(output_layer,item.entity,object_id,staging,payload,len(logical)))
            except Exception:
                if staging.exists(): shutil.rmtree(staging)
                raise
            row_counts[item.entity]=len(logical)
        checks=pipeline.quality_checks(output_layer,parent,objects,row_counts,errors,warnings,expected_columns); passed=all(checks.values())
        validation=ValidationResult(passed=passed,checks=checks,errors=errors+([] if passed else ["Layer quality gate failed."]),warnings=warnings,rejected_rows=sum(rejected.values()))
        manifest_id=_hash("lake-manifest",{"layer":output_layer.value,"dataset":parent.dataset_id,"version":version,"engine":"spark","format":"parquet","parent":source.snapshot_id,"logical_objects":[{"entity":item.entity,"checksum":item.checksum,"rows":item.row_count} for item in objects],"validation":validation.model_dump(mode="json")})
        manifest=LayerManifest(manifest_id=manifest_id,layer=output_layer,dataset_id=parent.dataset_id,transformation_name=name,transformation_version=version,parent_ids=[source.snapshot_id],objects=objects,row_counts=row_counts,rejected_row_counts=rejected,validation=validation)
        pipeline.store.register_layer_manifest(manifest)
        metadata={**source.metadata,"execution_engine":"spark","engine_version":spark.version,"spark_application_id":spark.sparkContext.applicationId,"spark_master":spark.sparkContext.master,"physical_format":"parquet"}
        snapshot_id=_hash("lake-snapshot",{"manifest":manifest_id,"layer":output_layer.value,"parents":[source.snapshot_id]}); candidate=PublishedSnapshot(snapshot_id=snapshot_id,layer=output_layer,layer_manifest_id=manifest_id,dataset_id=parent.dataset_id,parent_snapshot_ids=[source.snapshot_id],object_ids=[item.object_id for item in objects],status="validated" if passed else "failed",metadata=metadata)
        published=pipeline.store.publish_snapshot(candidate) if passed else candidate
        if passed: pipeline.store.register_edge(LineageEdge(parent_id=source.snapshot_id,child_id=published.snapshot_id,relationship="transformed_to",transformation_name=name,transformation_version=version,checksums=[item.checksum for item in objects],validation_passed=True))
        completed=datetime.now(timezone.utc); run_id=_hash("transform-run",{"name":name,"version":version,"engine":"spark","input":source.snapshot_id,"output":manifest_id})
        return TransformationRun(run_id=run_id,definition=TransformationDefinition(name=name,version=version,input_layer=source.layer,output_layer=output_layer),input_ids=[source.snapshot_id],output_manifest_id=manifest_id,status="completed" if passed else "failed",validation=validation,started_at=started,completed_at=completed,orchestration_run_id=pipeline.orchestration_run_id,distributed_job_id=spark.sparkContext.applicationId,execution_engine="spark",engine_version=spark.version,spark_application_id=spark.sparkContext.applicationId,spark_master=spark.sparkContext.master,input_partition_count=input_partitions,output_partition_count=output_partitions,records_read=sum(item.row_count for item in parent.objects),records_written=sum(row_counts.values()),physical_format="parquet",transformation_implementation_version=version)
