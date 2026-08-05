"""Typed, engine-neutral logical records emitted by synthetic generation."""
from __future__ import annotations

from typing import NamedTuple


class PatientRecord(NamedTuple):
    patient_id: int; birth_date: str; sex: str; race_ethnicity: str | None
    insurance_type: str; residential_region: str | None; created_at: str


class HospitalRecord(NamedTuple):
    hospital_id: int; hospital_name: str; state: str; urban_rural: str
    bed_count: int; teaching_status: str; ownership_type: str


class ProviderRecord(NamedTuple):
    provider_id: int; hospital_id: int; specialty: str; years_experience: int


class EncounterRecord(NamedTuple):
    encounter_id: int; patient_id: int; hospital_id: int; provider_id: int
    encounter_type: str; admission_date: str; discharge_date: str
    discharge_disposition: str | None; total_cost: float; mortality_flag: int
    complication_flag: int


class DiagnosisRecord(NamedTuple):
    diagnosis_id: int; diagnosis_code: str; diagnosis_name: str; diagnosis_category: str


class EncounterDiagnosisRecord(NamedTuple):
    encounter_id: int; diagnosis_id: int; diagnosis_rank: int; primary_diagnosis_flag: int


class ProcedureRecord(NamedTuple):
    procedure_id: int; procedure_code: str; procedure_name: str; procedure_category: str


class EncounterProcedureRecord(NamedTuple):
    encounter_id: int; procedure_id: int; procedure_date: str


class LabResultRecord(NamedTuple):
    lab_result_id: int | None; encounter_id: int; lab_name: str; lab_value: float | None
    unit: str | None; reference_low: float | None; reference_high: float | None; collected_at: str


class ReadmissionRecord(NamedTuple):
    readmission_id: int; index_encounter_id: int; readmission_encounter_id: int | None
    days_to_readmission: int | None; readmitted_within_30_days: int


class QualityMeasureRecord(NamedTuple):
    quality_measure_id: int; hospital_id: int; measure_name: str
    measurement_period_start: str; measurement_period_end: str; numerator: int
    denominator: int; measure_value: float


LogicalRecord = (
    PatientRecord | HospitalRecord | ProviderRecord | EncounterRecord | DiagnosisRecord |
    EncounterDiagnosisRecord | ProcedureRecord | EncounterProcedureRecord |
    LabResultRecord | ReadmissionRecord | QualityMeasureRecord
)
