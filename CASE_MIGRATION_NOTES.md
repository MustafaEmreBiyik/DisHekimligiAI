# CASE_MIGRATION_NOTES

## Summary
- Normalized cases: 7
- Cases with [REVIEW_NEEDED]: 3
- schema_version set to 2.0 for all cases.
- Existing legacy structures were preserved; only canonical metadata fields were added.

## Per-case Decisions
- olp_001: title=Oral Liken Planus, category=oral_pathology, difficulty=intermediate, estimated_duration_minutes=20
- perio_001: title=Kronik Periodontitis (Riskli Hasta), category=periodontology, difficulty=advanced, estimated_duration_minutes=25
- herpes_primary_01: title=Primer Herpetik Gingivostomatitis, category=oral_infectious_disease, difficulty=intermediate, estimated_duration_minutes=20
- infectious_child_01: title=Primer Herpetik Gingivostomatitis (Pediatrik), category=oral_infectious_disease, difficulty=advanced, estimated_duration_minutes=25
- behcet_01: title=Behcet Hastaligi, category=oral_systemic_disease, difficulty=advanced, estimated_duration_minutes=30
- syphilis_02: title=Sekonder Sifiliz (Mukoz Plak), category=oral_infectious_disease, difficulty=advanced, estimated_duration_minutes=30
- desquamative_01: title=Kronik Deskuamatif Gingivitis, category=oral_pathology, difficulty=advanced, estimated_duration_minutes=30

## [REVIEW_NEEDED] Items
- behcet_01:
  - [REVIEW_NEEDED] estimated_duration_minutes and competencies should be clinically reviewed by faculty.
- syphilis_02:
  - [REVIEW_NEEDED] estimated_duration_minutes and competencies should be clinically reviewed by faculty.
- desquamative_01:
  - [REVIEW_NEEDED] estimated_duration_minutes and competencies should be clinically reviewed by faculty.
