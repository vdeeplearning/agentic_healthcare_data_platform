"""Explicit Spark schemas; imports PySpark only when Spark is selected."""
from __future__ import annotations

from src.lake.models import LakeLayer


# type name, nullable. Dates/timestamps remain ISO strings in lake logical content;
# serving loaders normalize them into native PostgreSQL types.
ENTITY_FIELDS={
 "patients":(("patient_id","long",False),("birth_date","string",False),("sex","string",False),("race_ethnicity","string",True),("insurance_type","string",False),("residential_region","string",True),("created_at","string",False)),
 "hospitals":(("hospital_id","long",False),("hospital_name","string",False),("state","string",False),("urban_rural","string",False),("bed_count","integer",False),("teaching_status","string",False),("ownership_type","string",False)),
 "providers":(("provider_id","long",False),("hospital_id","long",False),("specialty","string",False),("years_experience","integer",False)),
 "encounters":(("encounter_id","long",False),("patient_id","long",False),("hospital_id","long",False),("provider_id","long",True),("encounter_type","string",False),("admission_date","string",False),("discharge_date","string",True),("discharge_disposition","string",True),("total_cost","double",True),("mortality_flag","integer",False),("complication_flag","integer",False)),
 "diagnoses":(("diagnosis_id","long",False),("diagnosis_code","string",False),("diagnosis_name","string",False),("diagnosis_category","string",False)),
 "encounter_diagnoses":(("encounter_id","long",False),("diagnosis_id","long",False),("diagnosis_rank","integer",False),("primary_diagnosis_flag","integer",False)),
 "procedures":(("procedure_id","long",False),("procedure_code","string",False),("procedure_name","string",False),("procedure_category","string",False)),
 "encounter_procedures":(("encounter_id","long",False),("procedure_id","long",False),("procedure_date","string",False)),
 "lab_results":(("lab_result_id","long",True),("encounter_id","long",False),("lab_name","string",False),("lab_value","double",True),("unit","string",True),("reference_low","double",True),("reference_high","double",True),("collected_at","string",False)),
 "readmissions":(("readmission_id","long",False),("index_encounter_id","long",False),("readmission_encounter_id","long",True),("days_to_readmission","integer",True),("readmitted_within_30_days","integer",False)),
 "quality_measures":(("quality_measure_id","long",False),("hospital_id","long",False),("measure_name","string",False),("measurement_period_start","string",False),("measurement_period_end","string",False),("numerator","integer",False),("denominator","integer",False),("measure_value","double",False)),
}


def schema_for(entity:str,layer:LakeLayer):
    """Return an explicit StructType for every entity/layer combination."""
    if entity not in ENTITY_FIELDS: raise KeyError(f"Unknown lake entity: {entity}")
    try:
        from pyspark.sql.types import DoubleType,IntegerType,LongType,StringType,StructField,StructType
    except ImportError as exc: raise RuntimeError("Spark schemas require the optional `spark` dependency group.") from exc
    types={"string":StringType,"long":LongType,"integer":IntegerType,"double":DoubleType}
    # `layer` is intentionally accepted: logical columns remain stable across layers.
    if not isinstance(layer,LakeLayer): raise ValueError(layer)
    return StructType([StructField(name,types[kind](),nullable) for name,kind,nullable in ENTITY_FIELDS[entity]])


def physical_schema_for(entity:str,layer:LakeLayer):
    from pyspark.sql.types import ArrayType,LongType,StringType,StructField,StructType
    logical=schema_for(entity,layer)
    return StructType(list(logical.fields)+[
        StructField("_lake_row_order",LongType(),False),
        StructField("_lake_source_batch_id",StringType(),True),
        StructField("_lake_record_hash",StringType(),False),
        StructField("_lake_quality_flags",ArrayType(StringType()),False),
        StructField("_lake_rejection_reason",StringType(),True),
    ])
