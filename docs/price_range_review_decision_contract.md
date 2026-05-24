# PriceRange Review Decision Contract (QF5.2)

## Purpose

`PriceRange Review Decision` records the human review outcome for a candidate `PriceRange`.

It is used to decide whether a statistical candidate range can move forward as cloud-ready candidate data, remain in review, be archived, or be kept only as historical evidence.

## Important Boundary

`approved_for_cloud` is not formal price approval.

It only means the `PriceRange` may be uploaded as candidate statistical data for the next layer:

`Raw Candidate Warehouse -> Pricing / Method Review`

It does not create:
- formal `unit_price`
- `PricingRule`
- `MaterialSpec`
- `LaborRule`
- `BudgetEstimateLine`
- final quote output

## Decision Enum

- `approved_for_cloud`: The range is acceptable as candidate statistical data for the next review layer.
- `rejected`: This range is not used in the current candidate set, but source `PriceObservation` records are preserved.
- `needs_more_observations`: The range does not have enough included observations.
- `needs_unit_review`: Units such as `M2` and `PING` require human confirmation before the range can move forward.
- `needs_scope_review`: `labor_only`, `labor_and_material`, `equipment_allowance`, or `unknown` requires human confirmation.
- `needs_alias_review`: `canonical_item_code` or canonical identity requires human confirmation.
- `keep_as_historical_reference`: Preserve the record as evidence, but do not move it into the candidate price range set.

## Required Decision Fields

Each decision payload must include:
- `decision_id`
- `price_range_id`
- `reviewer_id`
- `decision`
- `suggested_decision`
- `decision_reason_codes`
- `reviewer_note`
- `decided_at`
- `source_observation_ids`
- `excluded_observation_ids`
- `upload_stage`
- `schema_version`
- `is_simulated_review`

## Application Rules

When `decision = approved_for_cloud`:
- `upload_stage` becomes `approved_for_cloud`
- `requires_human_review` becomes `false`
- the range remains candidate data only

When `decision != approved_for_cloud`:
- `requires_human_review` remains `true`
- `upload_stage` remains `review_required` or becomes `archived`

## Safety

Review decisions must never generate:
- `unit_price`
- `formal_price`
- `approved_price`
- `pricing_rule_id`
- `budget_estimate_line_id`

The reviewed range is still a candidate statistical artifact, not a formal price record.
