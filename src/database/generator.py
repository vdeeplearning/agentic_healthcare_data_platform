"""Storage-independent, versioned synthetic healthcare record generation."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterator

import numpy as np

from src.database.lifecycle import DatasetManifest, LogicalRecordBatch, new_manifest
from src.database.records import (
    DiagnosisRecord, EncounterDiagnosisRecord, EncounterProcedureRecord, EncounterRecord,
    HospitalRecord, LabResultRecord, PatientRecord, ProcedureRecord, ProviderRecord,
    QualityMeasureRecord, ReadmissionRecord,
)


DIAGNOSES = (
    DiagnosisRecord(1,"I50.9","Heart failure","cardiovascular"), DiagnosisRecord(2,"E11.9","Type 2 diabetes","endocrine"),
    DiagnosisRecord(3,"N18.9","Chronic kidney disease","renal"), DiagnosisRecord(4,"J18.9","Pneumonia","respiratory"),
    DiagnosisRecord(5,"I10","Hypertension","cardiovascular"), DiagnosisRecord(6,"A41.9","Sepsis","infectious"),
    DiagnosisRecord(7,"J44.1","COPD exacerbation","respiratory"), DiagnosisRecord(8,"S72.0","Hip fracture","injury"),
    DiagnosisRecord(9,"R07.9","Chest pain","symptom"), DiagnosisRecord(10,"X99.?","Inconsistent test code","data_quality"),
)
PROCEDURES = (
    ProcedureRecord(1,"PROC001","Echocardiogram","diagnostic"), ProcedureRecord(2,"PROC002","CT scan","imaging"),
    ProcedureRecord(3,"PROC003","Dialysis","therapeutic"), ProcedureRecord(4,"PROC004","Cardiac catheterization","therapeutic"),
)


class SyntheticRecordGenerator:
    """Emit deterministic entity batches without knowing their storage target."""

    def __init__(self, seed: int = 42, patients: int = 25_000, encounters: int = 100_000, batch_size: int = 5_000):
        self.seed = seed
        self.patients = patients
        self.encounters = encounters
        self.batch_size = batch_size
        self.manifest: DatasetManifest = new_manifest(seed, patients, encounters)

    @staticmethod
    def _batch(entity: str, records: list | tuple) -> LogicalRecordBatch:
        return LogicalRecordBatch(entity=entity, records=tuple(records))

    def batches(self) -> Iterator[LogicalRecordBatch]:
        rng = np.random.default_rng(self.seed)
        states = ["NY","PA","OH","NC","GA","IL"]
        hospitals: list[HospitalRecord] = []
        for hospital_id in range(1, 31):
            rural = hospital_id > 22
            hospitals.append(HospitalRecord(hospital_id, f"Synthetic {'Regional' if rural else 'Medical'} Center {hospital_id:02d}", states[(hospital_id-1)%len(states)], "rural" if rural else "urban", int(rng.integers(25,180) if rural else rng.integers(180,900)), "teaching" if hospital_id%3==0 else "non-teaching", ["nonprofit","public","for-profit"][hospital_id%3]))
        yield self._batch("hospitals", hospitals)

        specialties = ["hospitalist","cardiology","emergency","endocrinology","nephrology","surgery"]
        providers = [ProviderRecord(i, (i-1)%30+1, specialties[i%len(specialties)], int(rng.integers(1,41))) for i in range(1,201)]
        yield self._batch("providers", providers)

        start_birth = date(1925,1,1)
        patient_batch: list[PatientRecord] = []
        for patient_id in range(1, self.patients+1):
            birth = start_birth + timedelta(days=int(rng.integers(0, 85*365)))
            race_choice = rng.choice(["White","Black","Hispanic","Asian","Other",None], p=[.46,.2,.18,.09,.05,.02])
            race = None if race_choice is None else str(race_choice)
            sex = str(rng.choice(["F","M","X"],p=[.505,.49,.005]))
            insurance = str(rng.choice(["commercial","medicare","medicaid","self-pay"],p=[.39,.35,.21,.05]))
            region_choice = rng.choice(["north","south","east","west",None],p=[.24,.24,.24,.24,.04])
            region = None if region_choice is None else str(region_choice)
            patient_batch.append(PatientRecord(patient_id,birth.isoformat(),sex,race,insurance,region,"2023-01-01T00:00:00Z"))
            if len(patient_batch) >= self.batch_size:
                yield self._batch("patients", patient_batch); patient_batch=[]
        if patient_batch: yield self._batch("patients", patient_batch)

        yield self._batch("diagnoses", DIAGNOSES)
        yield self._batch("procedures", PROCEDURES)

        provider_by_hospital={hospital_id:[provider.provider_id for provider in providers if provider.hospital_id==hospital_id] for hospital_id in range(1,31)}
        encounter_batch=[]; diagnosis_batch=[]; procedure_batch=[]; lab_batch=[]
        primary_by_enc: dict[int, int] = {}; eligible: list[tuple[int, int]] = []
        first = date(2023,1,1)
        for encounter_id in range(1, self.encounters+1):
            patient_id=int(rng.integers(1,self.patients+1)); hospital_id=int(rng.integers(1,31))
            provider_id=int(rng.choice(provider_by_hospital[hospital_id])); kind=str(rng.choice(["inpatient","emergency","outpatient"],p=[.37,.35,.28]))
            day=int(rng.integers(0,1095)); admission=first+timedelta(days=day)
            primary=int(rng.choice(np.arange(1,10),p=[.14,.16,.10,.13,.13,.08,.09,.06,.11])); primary_by_enc[encounter_id]=primary
            base_los={"inpatient":4,"emergency":1,"outpatient":0}[kind]
            los=max(0,int(rng.poisson(base_los + (2 if primary in (1,6) else 0))))
            discharge=admission+timedelta(days=los)
            if encounter_id % 10000 == 0: discharge=admission-timedelta(days=1)
            hospital_risk=(hospital_id%7-3)*.004; complication=float(rng.random() < max(.005,.035+hospital_risk+.03*(primary==6)))
            mortality=float(rng.random() < max(.001,.012+hospital_risk+.035*(primary==6)))
            cost=max(100.0,float(rng.lognormal(8.2+.18*los+.25*(primary in (1,3,6)),.55)))
            disposition="expired" if mortality else str(rng.choice(["home","skilled nursing","rehabilitation",None],p=[.75,.12,.1,.03]))
            encounter_batch.append(EncounterRecord(encounter_id,patient_id,hospital_id,provider_id,kind,admission.isoformat(),discharge.isoformat(),disposition,round(cost,2),int(mortality),int(complication)))
            diagnosis_batch.append(EncounterDiagnosisRecord(encounter_id,primary,1,1))
            if kind == "inpatient": eligible.append((encounter_id,hospital_id))
            if rng.random()<.36:
                secondary=int(rng.choice([2,3,5]))
                if secondary != primary: diagnosis_batch.append(EncounterDiagnosisRecord(encounter_id,secondary,2,0))
            if rng.random()<.18: procedure_batch.append(EncounterProcedureRecord(encounter_id,int(rng.integers(1,5)),admission.isoformat()))
            if rng.random()<.22:
                value=float(rng.normal(110+25*(primary==2),28)); lab_batch.append(LabResultRecord(None,encounter_id,"glucose",round(value,1),"mg/dL",70.0,110.0,admission.isoformat()+"T08:00:00"))
            if len(encounter_batch)>=self.batch_size:
                yield self._batch("encounters",encounter_batch); encounter_batch=[]
                yield self._batch("encounter_diagnoses",diagnosis_batch); diagnosis_batch=[]
                yield self._batch("encounter_procedures",procedure_batch); procedure_batch=[]
                yield self._batch("lab_results",lab_batch); lab_batch=[]
        for entity, records in (("encounters",encounter_batch),("encounter_diagnoses",diagnosis_batch),("encounter_procedures",procedure_batch),("lab_results",lab_batch)):
            if records: yield self._batch(entity,records)

        readmission_batch=[]
        for readmission_id,(encounter_id,hospital_id) in enumerate(eligible,1):
            primary=primary_by_enc[encounter_id]
            risk=.09+.07*(primary in (1,6))+.035*(primary==3)+(hospital_id%6)*.008
            readmitted=int(rng.random()<risk); days=int(rng.integers(2,31)) if readmitted else None
            readmission_batch.append(ReadmissionRecord(readmission_id,encounter_id,None,days,readmitted))
            if len(readmission_batch)>=self.batch_size:
                yield self._batch("readmissions",readmission_batch); readmission_batch=[]
        if readmission_batch: yield self._batch("readmissions",readmission_batch)

        quality_batch=[]; quality_id=1
        for year in (2024,2025):
            for quarter in range(1,5):
                month=(quarter-1)*3+1; start=date(year,month,1); end=date(year+1,1,1)-timedelta(days=1) if quarter==4 else date(year,month+3,1)-timedelta(days=1)
                for hospital_id in range(1,31):
                    denominator=int(rng.integers(8,45) if hospital_id>=28 else rng.integers(80,350)); trend=-.006*(year-2024)*4-.004*(quarter-1)
                    rate=float(np.clip(.08+(hospital_id%6)*.012+trend+rng.normal(0,.008),.02,.35)); numerator=int(round(denominator*rate))
                    quality_batch.append(QualityMeasureRecord(quality_id,hospital_id,"30-day readmission rate",start.isoformat(),end.isoformat(),numerator,denominator,numerator/denominator)); quality_id+=1
        yield self._batch("quality_measures",quality_batch)
