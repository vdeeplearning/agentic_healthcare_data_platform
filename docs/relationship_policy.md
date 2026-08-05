# Relationship-policy characterization

The catalog currently declares these approved relationships:

- encounters.patient_id ↔ patients.patient_id
- encounters.hospital_id ↔ hospitals.hospital_id
- encounters.provider_id ↔ providers.provider_id
- providers.hospital_id ↔ hospitals.hospital_id
- encounter_diagnoses.encounter_id ↔ encounters.encounter_id
- encounter_diagnoses.diagnosis_id ↔ diagnoses.diagnosis_id
- encounter_procedures.encounter_id ↔ encounters.encounter_id
- encounter_procedures.procedure_id ↔ procedures.procedure_id
- lab_results.encounter_id ↔ encounters.encounter_id
- readmissions.index_encounter_id ↔ encounters.encounter_id
- readmissions.readmission_encounter_id ↔ encounters.encounter_id
- quality_measures.hospital_id ↔ hospitals.hospital_id

Today this is metadata, not an enforced allowlist. The validator rejects a join with no meaningful `ON` or `USING` predicate, but accepts an equality predicate such as `hospitals.hospital_id = patients.patient_id` even though it is not registered. Tests preserve this behavior and list examples that strict enforcement would newly reject.

The intended future contract is: every base-table join edge must resolve through aliases and match an approved relationship in either direction, unless a separately registered derived relationship applies. Before activation, the implementation must specify composite-key handling, CTE and view lineage, self-joins, multiple predicates, and error messages. Enforcement belongs in a separately reviewed safety milestone.
