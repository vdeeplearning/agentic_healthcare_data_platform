# Database schema

The normalized model separates people, facilities, providers, encounters, vocabulary, bridge tables, labs, readmission episodes, quarterly measures, and audit runs. Foreign keys are enabled on every connection. Composite keys prevent duplicate bridge rows; checks constrain flags, categories, rates, and denominators; indexes cover dates and common joins. `encounter_facts` and `hospital_readmission_summary` demonstrate reusable views.

The generator is seeded and introduces meaningful hospital, diagnosis, temporal, and comorbidity patterns. Deliberate anomalies include negative stays, missing demographic/disposition values, an inconsistent diagnosis code, null-heavy optional fields, and low-volume quality-measure groups. Nothing represents a real person or institution.

`audit_runs` retains its original columns and adds nullable `provenance_json` for deterministic dataset, manifest, and snapshot references. Old tables are upgraded additively and old rows remain readable with null provenance.

Platform lineage metadata is deliberately stored outside the analytical catalog in an adjacent migrated SQLite sidecar. `dataset_manifests` stores logical dataset descriptions; `dataset_snapshots` stores concrete materializations and active/superseded status; `platform_metadata_migrations` records applied metadata schema versions. These tables are not available to analytical SQL or the model.

