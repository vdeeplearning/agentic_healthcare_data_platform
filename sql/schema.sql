PRAGMA foreign_keys = ON;
BEGIN;
CREATE TABLE IF NOT EXISTS patients (
 patient_id INTEGER PRIMARY KEY, birth_date TEXT NOT NULL, sex TEXT NOT NULL CHECK(sex IN ('F','M','X')),
 race_ethnicity TEXT, insurance_type TEXT NOT NULL, residential_region TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hospitals (
 hospital_id INTEGER PRIMARY KEY, hospital_name TEXT NOT NULL UNIQUE, state TEXT NOT NULL,
 urban_rural TEXT NOT NULL CHECK(urban_rural IN ('urban','rural')), bed_count INTEGER NOT NULL CHECK(bed_count>0),
 teaching_status TEXT NOT NULL, ownership_type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS providers (
 provider_id INTEGER PRIMARY KEY, hospital_id INTEGER NOT NULL REFERENCES hospitals(hospital_id),
 specialty TEXT NOT NULL, years_experience INTEGER NOT NULL CHECK(years_experience BETWEEN 0 AND 60)
);
CREATE TABLE IF NOT EXISTS encounters (
 encounter_id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL REFERENCES patients(patient_id),
 hospital_id INTEGER NOT NULL REFERENCES hospitals(hospital_id), provider_id INTEGER REFERENCES providers(provider_id),
 encounter_type TEXT NOT NULL CHECK(encounter_type IN ('inpatient','emergency','outpatient')),
 admission_date TEXT NOT NULL, discharge_date TEXT, discharge_disposition TEXT, total_cost REAL CHECK(total_cost>=0),
 mortality_flag INTEGER NOT NULL CHECK(mortality_flag IN (0,1)), complication_flag INTEGER NOT NULL CHECK(complication_flag IN (0,1))
);
CREATE TABLE IF NOT EXISTS diagnoses (
 diagnosis_id INTEGER PRIMARY KEY, diagnosis_code TEXT NOT NULL, diagnosis_name TEXT NOT NULL, diagnosis_category TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS encounter_diagnoses (
 encounter_id INTEGER NOT NULL REFERENCES encounters(encounter_id), diagnosis_id INTEGER NOT NULL REFERENCES diagnoses(diagnosis_id),
 diagnosis_rank INTEGER NOT NULL CHECK(diagnosis_rank>0), primary_diagnosis_flag INTEGER NOT NULL CHECK(primary_diagnosis_flag IN (0,1)),
 PRIMARY KEY(encounter_id, diagnosis_id)
);
CREATE TABLE IF NOT EXISTS procedures (
 procedure_id INTEGER PRIMARY KEY, procedure_code TEXT NOT NULL UNIQUE, procedure_name TEXT NOT NULL, procedure_category TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS encounter_procedures (
 encounter_id INTEGER NOT NULL REFERENCES encounters(encounter_id), procedure_id INTEGER NOT NULL REFERENCES procedures(procedure_id),
 procedure_date TEXT NOT NULL, PRIMARY KEY(encounter_id, procedure_id)
);
CREATE TABLE IF NOT EXISTS lab_results (
 lab_result_id INTEGER PRIMARY KEY, encounter_id INTEGER NOT NULL REFERENCES encounters(encounter_id), lab_name TEXT NOT NULL,
 lab_value REAL, unit TEXT, reference_low REAL, reference_high REAL, collected_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS readmissions (
 readmission_id INTEGER PRIMARY KEY, index_encounter_id INTEGER NOT NULL UNIQUE REFERENCES encounters(encounter_id),
 readmission_encounter_id INTEGER REFERENCES encounters(encounter_id), days_to_readmission INTEGER,
 readmitted_within_30_days INTEGER NOT NULL CHECK(readmitted_within_30_days IN (0,1)),
 CHECK(days_to_readmission IS NULL OR days_to_readmission>=0)
);
CREATE TABLE IF NOT EXISTS quality_measures (
 quality_measure_id INTEGER PRIMARY KEY, hospital_id INTEGER NOT NULL REFERENCES hospitals(hospital_id), measure_name TEXT NOT NULL,
 measurement_period_start TEXT NOT NULL, measurement_period_end TEXT NOT NULL, numerator INTEGER NOT NULL,
 denominator INTEGER NOT NULL CHECK(denominator>0), measure_value REAL NOT NULL CHECK(measure_value BETWEEN 0 AND 1),
 UNIQUE(hospital_id, measure_name, measurement_period_start)
);
CREATE TABLE IF NOT EXISTS audit_runs (
 run_id TEXT PRIMARY KEY, user_question TEXT NOT NULL, normalized_question TEXT NOT NULL, model_name TEXT NOT NULL,
 schema_version TEXT NOT NULL, analysis_plan_json TEXT, generated_sql TEXT, validation_status TEXT NOT NULL,
 execution_status TEXT NOT NULL, result_row_count INTEGER NOT NULL DEFAULT 0, execution_time_ms REAL,
 statistical_tools_json TEXT, warnings_json TEXT, final_answer TEXT, created_at TEXT NOT NULL,
 provenance_json TEXT
);
COMMIT;

