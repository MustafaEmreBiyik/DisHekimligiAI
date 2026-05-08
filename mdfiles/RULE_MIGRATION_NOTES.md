# RULE_MIGRATION_NOTES

## Summary
- Rule sets normalized: 7
- Total rules updated: 34
- Rules marked is_critical_safety_rule=true: 8
- schema_version set to 2.0 for all rule sets.
- competency_tags added for every rule.

## Safety Category Mapping
- premature_treatment | wrong_medication | missed_critical_step | contraindication_violation
- Negative score rules were force-marked as critical safety rules.

## [REVIEW_NEEDED] Items
- competency_tags and safety_category assignments are heuristic and should be faculty-reviewed.
